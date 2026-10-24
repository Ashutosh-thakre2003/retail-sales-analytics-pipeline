from datetime import date
from decimal import Decimal

import pytest
from pyspark.sql import SparkSession

from quality import (
    EXPECTED_COLUMNS,
    apply_types,
    check_columns,
    split_valid_rejected,
)

VALID_ROW = {
    "Row ID": "1",
    "Order ID": "CA-2016-152156",
    "Order Date": "11/8/2016",
    "Ship Date": "11/11/2016",
    "Ship Mode": "Second Class",
    "Customer ID": "CG-12520",
    "Customer Name": "Claire Gute",
    "Segment": "Consumer",
    "Country": "United States",
    "City": "Henderson",
    "State": "Kentucky",
    "Postal Code": "42420",
    "Region": "South",
    "Product ID": "FUR-BO-10001798",
    "Category": "Furniture",
    "Sub-Category": "Bookcases",
    "Product Name": "Bush Somerset Collection Bookcase",
    "Sales": "261.96",
    "Quantity": "2",
    "Discount": "0",
    "Profit": "41.9136",
}


@pytest.fixture(scope="session")
def spark():
    session = (
        SparkSession.builder
        .appName("QualityTests")
        .master("local[1]")
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    session.sparkContext.setLogLevel("ERROR")
    yield session
    session.stop()


def make_raw(spark, *overrides):
    rows = []
    for index, override in enumerate(overrides, start=1):
        row = {**VALID_ROW, "Row ID": str(index), **override}
        rows.append(tuple(row[c] for c in EXPECTED_COLUMNS))
    return spark.createDataFrame(rows, EXPECTED_COLUMNS)


def run(spark, *overrides):
    clean, rejected = split_valid_rejected(apply_types(make_raw(spark, *overrides)))
    reasons = {
        r["row_id"]: r["rejection_reason"] for r in rejected.collect()
    }
    return clean.collect(), reasons


def test_valid_row_is_typed_and_kept(spark):
    clean, reasons = run(spark, {})
    assert reasons == {}
    assert len(clean) == 1
    row = clean[0]
    assert row["order_date"] == date(2016, 11, 8)
    assert row["ship_date"] == date(2016, 11, 11)
    assert row["sales"] == Decimal("261.9600")
    assert row["quantity"] == 2
    assert row["profit"] == Decimal("41.9136")


def test_whitespace_is_trimmed(spark):
    clean, _ = run(spark, {"Customer Name": "  Claire Gute  ", "Sales": " 10.5 "})
    assert clean[0]["customer_name"] == "Claire Gute"
    assert clean[0]["sales"] == Decimal("10.5000")


@pytest.mark.parametrize(
    "override, reason",
    [
        ({"Order Date": "2016-13-45"}, "invalid_order_date"),
        ({"Ship Date": "not a date"}, "invalid_ship_date"),
        ({"Sales": "abc"}, "invalid_sales"),
        ({"Quantity": "two"}, "invalid_quantity"),
        ({"Profit": ""}, "invalid_profit"),
        ({"Sales": "-5"}, "negative_sales"),
        ({"Quantity": "0"}, "nonpositive_quantity"),
        ({"Discount": "1.5"}, "discount_out_of_range"),
        ({"Ship Date": "11/1/2016"}, "ship_before_order"),
        ({"Customer ID": "  "}, "missing_customer_id"),
        ({"Postal Code": ""}, "missing_postal_code"),
        ({"Row ID": "x"}, "invalid_row_id"),
    ],
)
def test_invalid_values_are_rejected(spark, override, reason):
    clean, rejected = split_valid_rejected(apply_types(make_raw(spark, override)))
    assert clean.count() == 0
    assert reason in rejected.first()["rejection_reason"]


def test_duplicate_row_ids_reject_both_rows(spark):
    raw = make_raw(spark, {"Row ID": "7"}, {"Row ID": "7"}, {})
    clean, rejected = split_valid_rejected(apply_types(raw))
    assert clean.count() == 1
    reasons = [r["rejection_reason"] for r in rejected.collect()]
    assert reasons == ["duplicate_row_id", "duplicate_row_id"]


def test_multiple_reasons_are_combined(spark):
    _, reasons = run(spark, {"Sales": "-1", "Quantity": "0"})
    assert reasons[1] == "negative_sales; nonpositive_quantity"


def test_rows_are_never_lost(spark):
    overrides = [{}, {"Sales": "bad"}, {"Discount": "2"}, {}]
    clean, rejected = split_valid_rejected(apply_types(make_raw(spark, *overrides)))
    assert clean.count() + rejected.count() == len(overrides)


def test_missing_source_column_raises(spark):
    raw = make_raw(spark, {}).drop("Profit")
    with pytest.raises(ValueError, match="Profit"):
        check_columns(raw)
