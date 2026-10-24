
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

CLEAN_PATH = "/workspace/data/processed/sales_cleaned"


def main():
    spark = (
        SparkSession.builder
        .appName("VerifyCleanedSales")
        .master("local[*]")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("ERROR")

    try:
        df = spark.read.parquet(CLEAN_PATH)

        print("\n=== DATASET SUMMARY ===")
        print(f"Rows: {df.count():,}")
        print(f"Columns: {len(df.columns)}")

        print("\n=== SCHEMA ===")
        df.printSchema()

        print("\n=== NULL CHECK ===")
        df.select([
            F.sum(
                F.when(F.col(c).isNull(), 1).otherwise(0)
            ).alias(c)
            for c in df.columns
        ]).show(truncate=False)

        print("\n=== BUSINESS SUMMARY ===")
        df.agg(
            F.countDistinct("order_id").alias("unique_orders"),
            F.countDistinct("customer_id").alias("unique_customers"),
            F.countDistinct("product_id").alias("unique_products"),
            F.round(F.sum("sales"), 2).alias("total_sales"),
            F.round(F.sum("profit"), 2).alias("total_profit"),
            F.sum("quantity").alias("total_quantity"),
            F.round(F.avg("discount"), 4).alias("average_discount"),
        ).show(truncate=False)

        print("\n=== SALES BY REGION ===")
        df.groupBy("region").agg(
            F.countDistinct("order_id").alias("orders"),
            F.round(F.sum("sales"), 2).alias("total_sales"),
            F.round(F.sum("profit"), 2).alias("total_profit"),
        ).orderBy(F.desc("total_sales")).show(truncate=False)

        print("\n=== DATE RANGE ===")
        df.agg(
            F.min("order_date").alias("first_order_date"),
            F.max("order_date").alias("last_order_date"),
            F.min("ship_date").alias("first_ship_date"),
            F.max("ship_date").alias("last_ship_date"),
        ).show(truncate=False)

    finally:
        spark.stop()


if __name__ == "__main__":
    main()
