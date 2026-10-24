"""Validate the local PySpark and Spark SQL environment."""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


def main() -> None:
    spark = (
        SparkSession.builder
        .appName("RetailSalesAnalyticsEnvironmentTest")
        .master("local[*]")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")

    try:
        print("=" * 60)
        print("RETAIL SALES ANALYTICS: ENVIRONMENT VALIDATION")
        print("=" * 60)

        print(f"Spark version: {spark.version}")
        print(f"Application name: {spark.sparkContext.appName}")
        print(f"Execution mode: {spark.sparkContext.master}")

        # Small test dataset. This is not the actual retail dataset.
        sales_data = [
            ("ORD001", "West", 250.00, 40.00),
            ("ORD002", "East", 180.00, 25.00),
            ("ORD003", "West", 320.00, 60.00),
            ("ORD004", "South", 150.00, 10.00),
        ]

        columns = ["order_id", "region", "sales", "profit"]

        df = spark.createDataFrame(sales_data, columns)

        print("\n1. Input DataFrame")
        df.show(truncate=False)

        # Basic data quality checks.
        row_count = df.count()
        null_count = df.select(
            F.sum(
                F.when(F.col("order_id").isNull(), 1).otherwise(0)
            ).alias("null_order_ids"),
            F.sum(
                F.when(F.col("sales").isNull(), 1).otherwise(0)
            ).alias("null_sales"),
        ).first()

        duplicate_order_count = (
            df.groupBy("order_id")
            .count()
            .filter(F.col("count") > 1)
            .count()
        )

        assert row_count == 4, f"Expected 4 rows, got {row_count}"
        assert null_count["null_order_ids"] == 0, "Null order IDs found"
        assert null_count["null_sales"] == 0, "Null sales values found"
        assert duplicate_order_count == 0, "Duplicate order IDs found"

        print("\n2. Data quality checks")
        print(f"Rows: {row_count}")
        print(f"Null order IDs: {null_count['null_order_ids']}")
        print(f"Null sales values: {null_count['null_sales']}")
        print(f"Duplicate order IDs: {duplicate_order_count}")

        # Spark SQL aggregation.
        df.createOrReplaceTempView("sales")

        print("\n3. Spark SQL: Sales and profit by region")

        result = spark.sql("""
            SELECT
                region,
                COUNT(*) AS order_count,
                ROUND(SUM(sales), 2) AS total_sales,
                ROUND(SUM(profit), 2) AS total_profit
            FROM sales
            GROUP BY region
            ORDER BY total_sales DESC
        """)

        result.show(truncate=False)

        # Validate aggregate results against known expected values.
        totals = df.agg(
            F.round(F.sum("sales"), 2).alias("total_sales"),
            F.round(F.sum("profit"), 2).alias("total_profit"),
        ).first()

        assert totals["total_sales"] == 900.00, (
            f"Unexpected sales total: {totals['total_sales']}"
        )
        assert totals["total_profit"] == 135.00, (
            f"Unexpected profit total: {totals['total_profit']}"
        )

        print("\n4. Aggregate validation")
        print(f"Total sales: {totals['total_sales']:.2f}")
        print(f"Total profit: {totals['total_profit']:.2f}")

        print("\nPASS: PySpark, Spark SQL, DataFrames, and basic "
              "data quality checks are working.")

    finally:
        spark.stop()


if __name__ == "__main__":
    main()
