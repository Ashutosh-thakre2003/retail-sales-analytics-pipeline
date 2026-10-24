
from decimal import Decimal

from pyspark.sql import SparkSession, functions as F

import db

PARQUET_PATH = "/workspace/data/processed/sales_cleaned"
JDBC_JAR = "/opt/spark-jars/postgresql-jdbc.jar"

DB_USER = db.DB_USER
DB_PASSWORD = db.db_password()
JDBC_URL = db.jdbc_url()


def main():
    spark = (
        SparkSession.builder
        .appName("RetailSalesToPostgres")
        .master("local[*]")
        .config("spark.jars", JDBC_JAR)
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")

    try:
        df = spark.read.parquet(PARQUET_PATH)

        source = df.agg(
            F.count("*").alias("rows"),
            F.round(F.sum("sales"), 2).alias("sales"),
            F.round(F.sum("profit"), 2).alias("profit"),
            F.countDistinct("order_id").alias("orders"),
        ).first()

        source_rows = source["rows"]
        source_sales = Decimal(str(source["sales"]))
        source_profit = Decimal(str(source["profit"]))
        source_orders = source["orders"]

        print("=== SOURCE ===")
        print(f"Rows: {source_rows:,}")
        print(f"Distinct orders: {source_orders:,}")
        print(f"Sales: {source_sales:,.2f}")
        print(f"Profit: {source_profit:,.2f}")

        # Refresh the staging table from the cleaned Parquet data.
        (
            df.write.format("jdbc")
            .option("url", JDBC_URL)
            .option("dbtable", "analytics.stg_sales")
            .option("user", DB_USER)
            .option("password", DB_PASSWORD)
            .option("driver", "org.postgresql.Driver")
            .option("batchsize", "1000")
            .mode("overwrite")
            .save()
        )

        print("\nStaging table written successfully.")

        # Dimensions and facts are loaded in one transaction.
        with db.connect() as conn:
            with conn.cursor() as cur:

                # Customer IDs must have consistent attributes.
                cur.execute("""
                    SELECT COUNT(*)
                    FROM (
                        SELECT customer_id
                        FROM analytics.stg_sales
                        GROUP BY customer_id
                        HAVING COUNT(
                            DISTINCT (customer_name, segment)
                        ) > 1
                    ) conflicts
                """)

                if cur.fetchone()[0] > 0:
                    raise RuntimeError(
                        "A customer ID has inconsistent name or segment."
                    )

                # Product IDs may have multiple names, but their categories
                # and subcategories must remain consistent.
                cur.execute("""
                    SELECT COUNT(*)
                    FROM (
                        SELECT product_id
                        FROM analytics.stg_sales
                        GROUP BY product_id
                        HAVING COUNT(
                            DISTINCT (category, sub_category)
                        ) > 1
                    ) conflicts
                """)

                if cur.fetchone()[0] > 0:
                    raise RuntimeError(
                        "A product ID has inconsistent category "
                        "or subcategory."
                    )

                # Date dimension: a contiguous calendar covering whole years
                # from the first order to the last shipment. Power BI time
                # intelligence requires a date table without gaps.
                cur.execute("""
                    INSERT INTO analytics.dim_date (
                        date_key, full_date, calendar_year,
                        quarter_number, month_number, month_name,
                        week_number, day_of_month, day_of_week,
                        day_name, is_weekend
                    )
                    SELECT
                        TO_CHAR(d.full_date, 'YYYYMMDD')::INTEGER,
                        d.full_date,
                        EXTRACT(YEAR FROM d.full_date)::SMALLINT,
                        EXTRACT(QUARTER FROM d.full_date)::SMALLINT,
                        EXTRACT(MONTH FROM d.full_date)::SMALLINT,
                        TO_CHAR(d.full_date, 'FMMonth'),
                        EXTRACT(WEEK FROM d.full_date)::SMALLINT,
                        EXTRACT(DAY FROM d.full_date)::SMALLINT,
                        EXTRACT(DOW FROM d.full_date)::SMALLINT + 1,
                        TO_CHAR(d.full_date, 'FMDay'),
                        EXTRACT(DOW FROM d.full_date) IN (0, 6)
                    FROM (
                        SELECT generate_series(
                            date_trunc('year', MIN(order_date)),
                            date_trunc('year', MAX(ship_date))
                                + INTERVAL '1 year - 1 day',
                            INTERVAL '1 day'
                        )::DATE AS full_date
                        FROM analytics.stg_sales
                    ) d
                    ON CONFLICT (full_date) DO UPDATE SET
                        calendar_year = EXCLUDED.calendar_year,
                        quarter_number = EXCLUDED.quarter_number,
                        month_number = EXCLUDED.month_number,
                        month_name = EXCLUDED.month_name,
                        week_number = EXCLUDED.week_number,
                        day_of_month = EXCLUDED.day_of_month,
                        day_of_week = EXCLUDED.day_of_week,
                        day_name = EXCLUDED.day_name,
                        is_weekend = EXCLUDED.is_weekend
                """)

                # Customer dimension.
                cur.execute("""
                    INSERT INTO analytics.dim_customer (
                        customer_id, customer_name, segment
                    )
                    SELECT DISTINCT
                        customer_id, customer_name, segment
                    FROM analytics.stg_sales
                    ON CONFLICT (customer_id) DO UPDATE SET
                        customer_name = EXCLUDED.customer_name,
                        segment = EXCLUDED.segment
                """)

                # Product dimension: preserve each distinct ID/name variant.
                cur.execute("""
                    INSERT INTO analytics.dim_product (
                        product_id, product_name, category, sub_category
                    )
                    SELECT DISTINCT
                        product_id, product_name, category, sub_category
                    FROM analytics.stg_sales
                    ON CONFLICT (product_id, product_name) DO UPDATE SET
                        category = EXCLUDED.category,
                        sub_category = EXCLUDED.sub_category
                """)

                # Geography dimension.
                cur.execute("""
                    INSERT INTO analytics.dim_geography (
                        country, state, city, postal_code, region
                    )
                    SELECT DISTINCT
                        country, state, city, postal_code, region
                    FROM analytics.stg_sales
                    ON CONFLICT (
                        country, state, city, postal_code, region
                    ) DO NOTHING
                """)

                # Shipping mode dimension.
                cur.execute("""
                    INSERT INTO analytics.dim_ship_mode (ship_mode)
                    SELECT DISTINCT ship_mode
                    FROM analytics.stg_sales
                    ON CONFLICT (ship_mode) DO NOTHING
                """)

                # Replace the fact snapshot within the transaction.
                cur.execute("DELETE FROM analytics.fact_sales")

                cur.execute("""
                    INSERT INTO analytics.fact_sales (
                        row_id, order_id, order_date_key, ship_date_key,
                        customer_key, product_key, geography_key,
                        ship_mode_key, quantity, sales, discount, profit
                    )
                    SELECT
                        s.row_id,
                        s.order_id,
                        od.date_key,
                        sd.date_key,
                        c.customer_key,
                        p.product_key,
                        g.geography_key,
                        sm.ship_mode_key,
                        s.quantity,
                        s.sales,
                        s.discount,
                        s.profit
                    FROM analytics.stg_sales s
                    JOIN analytics.dim_date od
                        ON od.full_date = s.order_date
                    JOIN analytics.dim_date sd
                        ON sd.full_date = s.ship_date
                    JOIN analytics.dim_customer c
                        ON c.customer_id = s.customer_id
                    JOIN analytics.dim_product p
                        ON p.product_id = s.product_id
                        AND p.product_name = s.product_name
                    JOIN analytics.dim_geography g
                        ON g.country = s.country
                        AND g.state = s.state
                        AND g.city = s.city
                        AND g.postal_code = s.postal_code
                        AND g.region = s.region
                    JOIN analytics.dim_ship_mode sm
                        ON sm.ship_mode = s.ship_mode
                """)

                # Reconcile loaded facts against the source metrics.
                cur.execute("""
                    SELECT
                        COUNT(*),
                        ROUND(COALESCE(SUM(sales), 0), 2),
                        ROUND(COALESCE(SUM(profit), 0), 2),
                        COUNT(DISTINCT order_id)
                    FROM analytics.fact_sales
                """)

                (
                    loaded_rows,
                    loaded_sales,
                    loaded_profit,
                    loaded_orders,
                ) = cur.fetchone()

                if (
                    loaded_rows != source_rows
                    or loaded_sales != source_sales
                    or loaded_profit != source_profit
                    or loaded_orders != source_orders
                ):
                    raise RuntimeError(
                        "Reconciliation failed. "
                        f"Rows: {loaded_rows}/{source_rows}; "
                        f"sales: {loaded_sales}/{source_sales}; "
                        f"profit: {loaded_profit}/{source_profit}; "
                        f"orders: {loaded_orders}/{source_orders}. "
                        "Transaction will be rolled back."
                    )

                dimension_counts = {}
                for table in (
                    "dim_date",
                    "dim_customer",
                    "dim_product",
                    "dim_geography",
                    "dim_ship_mode",
                ):
                    cur.execute(
                        f"SELECT COUNT(*) FROM analytics.{table}"
                    )
                    dimension_counts[table] = cur.fetchone()[0]

        print("\n=== LOAD SUCCEEDED ===")
        print(f"Fact rows: {loaded_rows:,}")
        print(f"Distinct orders: {loaded_orders:,}")
        print(f"Total sales: {loaded_sales:,.2f}")
        print(f"Total profit: {loaded_profit:,.2f}")

        print("\n=== DIMENSION COUNTS ===")
        for table, count in dimension_counts.items():
            print(f"{table}: {count:,}")

    finally:
        spark.stop()


if __name__ == "__main__":
    main()
