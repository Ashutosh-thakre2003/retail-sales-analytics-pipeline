
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

DATA_PATH = "/workspace/data/raw/Sample - Superstore.csv"


def main():
    spark = (
        SparkSession.builder
        .appName("RetailDatasetInspection")
        .master("local[*]")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")

    try:
        print("=" * 70)
        print("RETAIL DATASET INSPECTION")
        print("=" * 70)

        df = (
            spark.read
            .option("header", True)
            .option("inferSchema", True)
            .option("mode", "PERMISSIVE")
            .option("encoding", "UTF-8")
            .csv(DATA_PATH)
        )

        # 1. Schema
        print("\n1. COLUMN NAMES")
        for index, column in enumerate(df.columns, start=1):
            print(f"{index:2}. {column}")

        print("\n2. INFERRED SCHEMA")
        df.printSchema()

        # 2. Row count and sample
        row_count = df.count()
        column_count = len(df.columns)

        print(f"\n3. DATASET DIMENSIONS")
        print(f"Rows: {row_count:,}")
        print(f"Columns: {column_count}")

        print("\n4. SAMPLE RECORDS")
        df.show(10, truncate=False)

        # 3. Missing values
        print("\n5. MISSING VALUES BY COLUMN")

        null_expressions = [
            F.sum(
                F.when(
                    F.col(column).isNull()
                    | (
                        F.trim(F.col(column).cast("string")) == ""
                    ),
                    1,
                ).otherwise(0)
            ).alias(column)
            for column in df.columns
        ]

        null_counts = df.agg(*null_expressions).first().asDict()

        for column, count in null_counts.items():
            print(f"{column}: {count or 0:,}")

        # 4. Duplicate rows
        distinct_row_count = df.dropDuplicates().count()
        duplicate_rows = row_count - distinct_row_count

        print("\n6. DUPLICATE ROWS")
        print(f"Exact duplicate rows: {duplicate_rows:,}")

        # 5. Key-column checks, if these columns exist
        print("\n7. IDENTIFIER CHECKS")

        for column in ["Order ID", "Customer ID", "Product ID", "Row ID"]:
            if column in df.columns:
                print(f"\n{column}")

                print(
                    "Distinct values:",
                    df.select(column).distinct().count(),
                )

                print(
                    "Null values:",
                    null_counts.get(column, 0) or 0,
                )

        # 6. Numeric summaries
        print("\n8. NUMERIC COLUMN SUMMARY")

        numeric_columns = [
            column
            for column, dtype in df.dtypes
            if dtype in ("int", "bigint", "float", "double", "decimal")
        ]

        if numeric_columns:
            df.select(*numeric_columns).describe().show(truncate=False)
        else:
            print("No numeric columns were inferred.")

        # 7. Date inspection
        print("\n9. DATE RANGE")

        for column in ["Order Date", "Ship Date"]:
            if column in df.columns:
                parsed = F.coalesce(
                    F.to_date(F.col(column), "M/d/yyyy"),
                    F.to_date(F.col(column), "MM/dd/yyyy"),
                    F.to_date(F.col(column), "yyyy-MM-dd"),
                )

                date_stats = df.select(
                    F.min(parsed).alias("minimum_date"),
                    F.max(parsed).alias("maximum_date"),
                    F.sum(
                        F.when(
                            F.col(column).isNotNull() & parsed.isNull(),
                            1,
                        ).otherwise(0)
                    ).alias("unparsed_dates"),
                ).first()

                print(
                    f"{column}: "
                    f"min={date_stats['minimum_date']}, "
                    f"max={date_stats['maximum_date']}, "
                    f"unparsed={date_stats['unparsed_dates'] or 0}"
                )

        print("\nInspection completed successfully.")

    finally:
        spark.stop()


if __name__ == "__main__":
    main()
