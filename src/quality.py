"""Typing and data quality rules for the Superstore sales extract.

Kept separate from ingest_sales.py so the rules can be unit tested.
"""

from pyspark.sql import Window
from pyspark.sql import functions as F

EXPECTED_COLUMNS = [
    "Row ID", "Order ID", "Order Date", "Ship Date",
    "Ship Mode", "Customer ID", "Customer Name", "Segment",
    "Country", "City", "State", "Postal Code", "Region",
    "Product ID", "Category", "Sub-Category", "Product Name",
    "Sales", "Quantity", "Discount", "Profit",
]

REQUIRED_TEXT = [
    "order_id", "ship_mode", "customer_id", "customer_name",
    "segment", "country", "city", "state", "postal_code", "region",
    "product_id", "category", "sub_category", "product_name",
]


def check_columns(raw):
    missing_columns = sorted(set(EXPECTED_COLUMNS) - set(raw.columns))
    if missing_columns:
        raise ValueError(f"Missing required source columns: {missing_columns}")


def apply_types(raw):
    """Normalize column names and apply explicit types."""
    return raw.select(
        F.expr("try_cast(trim(`Row ID`) AS INT)").alias("row_id"),
        F.trim(F.col("Order ID")).alias("order_id"),
        F.try_to_timestamp(F.trim(F.col("Order Date")), F.lit("M/d/yyyy")).cast("date").alias("order_date"),
        F.try_to_timestamp(F.trim(F.col("Ship Date")), F.lit("M/d/yyyy")).cast("date").alias("ship_date"),
        F.trim(F.col("Ship Mode")).alias("ship_mode"),
        F.trim(F.col("Customer ID")).alias("customer_id"),
        F.trim(F.col("Customer Name")).alias("customer_name"),
        F.trim(F.col("Segment")).alias("segment"),
        F.trim(F.col("Country")).alias("country"),
        F.trim(F.col("City")).alias("city"),
        F.trim(F.col("State")).alias("state"),
        F.trim(F.col("Postal Code")).alias("postal_code"),
        F.trim(F.col("Region")).alias("region"),
        F.trim(F.col("Product ID")).alias("product_id"),
        F.trim(F.col("Category")).alias("category"),
        F.trim(F.col("Sub-Category")).alias("sub_category"),
        F.trim(F.col("Product Name")).alias("product_name"),
        F.expr("try_cast(trim(`Sales`) AS DECIMAL(18,4))").alias("sales"),
        F.expr("try_cast(trim(`Quantity`) AS INT)").alias("quantity"),
        F.expr("try_cast(trim(`Discount`) AS DECIMAL(9,4))").alias("discount"),
        F.expr("try_cast(trim(`Profit`) AS DECIMAL(18,4))").alias("profit"),
    )


def split_valid_rejected(typed):
    """Return (clean, rejected). Rejected rows carry a rejection_reason."""
    # Identify duplicate source row IDs without silently removing rows.
    checked = typed.withColumn(
        "_row_id_count",
        F.count(F.lit(1)).over(Window.partitionBy("row_id")),
    )

    reasons = [
        F.when(F.col("row_id").isNull(), "invalid_row_id"),
        F.when(F.col("_row_id_count") > 1, "duplicate_row_id"),
        F.when(F.col("order_date").isNull(), "invalid_order_date"),
        F.when(F.col("ship_date").isNull(), "invalid_ship_date"),
        F.when(F.col("sales").isNull(), "invalid_sales"),
        F.when(F.col("quantity").isNull(), "invalid_quantity"),
        F.when(F.col("discount").isNull(), "invalid_discount"),
        F.when(F.col("profit").isNull(), "invalid_profit"),
    ]

    for column in REQUIRED_TEXT:
        reasons.append(
            F.when(
                F.col(column).isNull() | (F.col(column) == ""),
                f"missing_{column}",
            )
        )

    reasons.extend([
        F.when(F.col("sales") < 0, "negative_sales"),
        F.when(F.col("quantity") <= 0, "nonpositive_quantity"),
        F.when(
            (F.col("discount") < 0) | (F.col("discount") > 1),
            "discount_out_of_range",
        ),
        F.when(
            F.col("order_date").isNotNull()
            & F.col("ship_date").isNotNull()
            & (F.col("ship_date") < F.col("order_date")),
            "ship_before_order",
        ),
    ])

    checked = checked.withColumn("rejection_reason", F.concat_ws("; ", *reasons))

    rejected = checked.filter(F.col("rejection_reason") != "").drop("_row_id_count")
    clean = (
        checked.filter(F.col("rejection_reason") == "")
        .drop("_row_id_count", "rejection_reason")
    )
    return clean, rejected
