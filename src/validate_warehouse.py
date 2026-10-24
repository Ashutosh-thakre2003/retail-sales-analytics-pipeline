"""Post-load checks on the warehouse and reporting layer.

Fails (non-zero exit) if any check does not pass, so the pipeline stops
before a broken model reaches Power BI.
"""

from decimal import Decimal

import pyarrow.parquet as pq

import db

PARQUET_PATH = "/workspace/data/processed/sales_cleaned"

# (description, SQL returning a single number, expected value)
CHECKS = [
    (
        "Date dimension has no gaps",
        """
        SELECT (MAX(full_date) - MIN(full_date) + 1) - COUNT(*)
        FROM analytics.dim_date
        """,
        0,
    ),
    (
        "Date dimension covers all order and ship dates",
        """
        SELECT COUNT(*) FROM analytics.fact_sales f
        WHERE NOT EXISTS (SELECT 1 FROM analytics.dim_date d
                          WHERE d.date_key = f.order_date_key)
           OR NOT EXISTS (SELECT 1 FROM analytics.dim_date d
                          WHERE d.date_key = f.ship_date_key)
        """,
        0,
    ),
    (
        "Fact row IDs are unique",
        "SELECT COUNT(*) - COUNT(DISTINCT row_id) FROM analytics.fact_sales",
        0,
    ),
    (
        "No ship date precedes its order date",
        "SELECT COUNT(*) FROM reporting.fact_sales WHERE ship_days < 0",
        0,
    ),
    (
        "Every customer dimension row is used by a fact",
        """
        SELECT COUNT(*) FROM analytics.dim_customer c
        WHERE NOT EXISTS (SELECT 1 FROM analytics.fact_sales f
                          WHERE f.customer_key = c.customer_key)
        """,
        0,
    ),
    (
        "Every product dimension row is used by a fact",
        """
        SELECT COUNT(*) FROM analytics.dim_product p
        WHERE NOT EXISTS (SELECT 1 FROM analytics.fact_sales f
                          WHERE f.product_key = p.product_key)
        """,
        0,
    ),
    (
        "Reporting fact view matches the fact table",
        """
        SELECT (SELECT COUNT(*) FROM reporting.fact_sales)
             - (SELECT COUNT(*) FROM analytics.fact_sales)
        """,
        0,
    ),
    (
        "Enriched view keeps every fact row (no join losses)",
        """
        SELECT (SELECT COUNT(*) FROM reporting.v_sales_enriched)
             - (SELECT COUNT(*) FROM analytics.fact_sales)
        """,
        0,
    ),
    (
        "Region view sales equal fact sales",
        """
        SELECT ROUND((SELECT SUM(sales) FROM reporting.v_region_kpis)
                   - (SELECT SUM(sales) FROM analytics.fact_sales), 0)
        """,
        0,
    ),
]


def main():
    clean = pq.read_table(PARQUET_PATH, columns=["sales", "profit"]).to_pandas()
    parquet_rows = len(clean)
    parquet_sales = round(Decimal(str(clean["sales"].sum())), 2)
    parquet_profit = round(Decimal(str(clean["profit"].sum())), 2)

    failures = []
    with db.connect() as conn, conn.cursor() as cur:
        for description, query, expected in CHECKS:
            cur.execute(query)
            actual = cur.fetchone()[0]
            ok = actual == expected
            print(f"[{'PASS' if ok else 'FAIL'}] {description} (got {actual})")
            if not ok:
                failures.append(description)

        cur.execute(
            "SELECT COUNT(*), ROUND(SUM(sales), 2), ROUND(SUM(profit), 2) "
            "FROM analytics.fact_sales"
        )
        rows, sales, profit = cur.fetchone()

    reconciled = (
        rows == parquet_rows
        and abs(sales - parquet_sales) <= Decimal("0.01")
        and abs(profit - parquet_profit) <= Decimal("0.01")
    )
    print(
        f"[{'PASS' if reconciled else 'FAIL'}] Warehouse reconciles with "
        f"cleaned Parquet (rows {rows}/{parquet_rows}, "
        f"sales {sales}/{parquet_sales}, profit {profit}/{parquet_profit})"
    )
    if not reconciled:
        failures.append("Parquet reconciliation")

    if failures:
        raise SystemExit(f"{len(failures)} warehouse check(s) failed: {failures}")
    print("All warehouse checks passed.")


if __name__ == "__main__":
    main()
