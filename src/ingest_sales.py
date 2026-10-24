
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from quality import apply_types, check_columns, split_valid_rejected

INPUT_PATH = "/workspace/data/raw/Sample - Superstore.csv"
CLEAN_PATH = "/workspace/data/processed/sales_cleaned"
REJECTED_PATH = "/workspace/data/quality/rejected_rows"


def main():
    spark = (
        SparkSession.builder
        .appName("RetailSalesIngestion")
        .master("local[*]")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")

    try:
        # Read source fields as strings to control type conversion explicitly.
        raw = (
            spark.read.option("header", True).option("encoding", "UTF-8").option("quote", '"').option("escape", '"').option("mode", "FAILFAST").csv(INPUT_PATH)
        )

        check_columns(raw)
        clean, rejected = split_valid_rejected(apply_types(raw))

        source_count = raw.count()
        clean_count = clean.count()
        rejected_count = rejected.count()

        # Verify that every source record is accounted for.
        if source_count != clean_count + rejected_count:
            raise RuntimeError(
                "Record reconciliation failed: source count does not "
                "equal clean count plus rejected count."
            )

        # Persist reproducible outputs. Parquet retains typed columns.
        clean.write.mode("overwrite").parquet(CLEAN_PATH)
        rejected.write.mode("overwrite").parquet(REJECTED_PATH)

        print("\n=== INGESTION SUMMARY ===")
        print(f"Source records:   {source_count:,}")
        print(f"Clean records:    {clean_count:,}")
        print(f"Rejected records: {rejected_count:,}")
        print(f"Reconciliation:   {clean_count + rejected_count:,}")

        print("\n=== CLEAN SCHEMA ===")
        clean.printSchema()

        print("\n=== SALES BY REGION ===")
        (
            clean.groupBy("region")
            .agg(
                F.countDistinct("order_id").alias("orders"),
                F.round(F.sum("sales"), 2).alias("total_sales"),
                F.round(F.sum("profit"), 2).alias("total_profit"),
            )
            .orderBy(F.desc("total_sales"))
            .show(truncate=False)
        )

        print("\n=== REJECTION REASONS ===")
        if rejected_count:
            (
                rejected.groupBy("rejection_reason")
                .count()
                .orderBy(F.desc("count"))
                .show(truncate=False)
            )
        else:
            print("No records rejected.")

        print(f"\nClean Parquet: {CLEAN_PATH}")
        print(f"Rejected Parquet: {REJECTED_PATH}")
        print("Ingestion completed successfully.")

    finally:
        spark.stop()


if __name__ == "__main__":
    main()
