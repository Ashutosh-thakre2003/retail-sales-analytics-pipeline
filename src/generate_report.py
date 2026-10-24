"""Generate the sales insights report and CSV extracts from reporting views.

Outputs:
    reports/sales_insights.md
    reports/extracts/<view>.csv
"""

from datetime import date
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

import db

REPORTS_DIR = Path("/workspace/reports")
EXTRACTS_DIR = REPORTS_DIR / "extracts"

EXTRACT_VIEWS = [
    "v_yearly_kpis",
    "v_monthly_kpis",
    "v_region_kpis",
    "v_state_kpis",
    "v_subcategory_kpis",
    "v_segment_kpis",
    "v_discount_impact",
    "v_ship_mode_kpis",
    "v_customer_summary",
    "v_top_products",
]


def money(value):
    value = float(value)
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.0f}"


def pct(value):
    return "n/a" if pd.isna(value) else f"{float(value) * 100:.1f}%"


def md_table(df, formats):
    headers = list(formats)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for _, row in df.iterrows():
        cells = [fmt(row) for fmt in formats.values()]
        lines.append("| " + " | ".join(str(c) for c in cells) + " |")
    return "\n".join(lines)


def main():
    engine = create_engine(db.sqlalchemy_url())
    EXTRACTS_DIR.mkdir(parents=True, exist_ok=True)

    frames = {}
    with engine.connect() as conn:
        for view in EXTRACT_VIEWS:
            df = pd.read_sql(f"SELECT * FROM reporting.{view}", conn)
            df.to_csv(EXTRACTS_DIR / f"{view}.csv", index=False)
            frames[view] = df
            print(f"Extracted reporting.{view}: {len(df):,} rows")

        totals = pd.read_sql(
            """
            SELECT COUNT(*) AS lines,
                   COUNT(DISTINCT order_id) AS orders,
                   COUNT(DISTINCT customer_id) AS customers,
                   COUNT(DISTINCT product_id) AS products,
                   SUM(sales) AS sales, SUM(profit) AS profit,
                   SUM(quantity) AS units,
                   SUM(discount_amount) AS discount_amount,
                   AVG(ship_days) AS avg_ship_days,
                   MIN(order_date) AS first_order, MAX(order_date) AS last_order,
                   AVG(discount) AS avg_discount,
                   AVG(is_loss::INT) AS loss_share,
                   SUM(CASE WHEN is_loss THEN profit ELSE 0 END) AS loss_amount
            FROM reporting.v_sales_enriched
            """,
            conn,
        ).iloc[0]

    yearly = frames["v_yearly_kpis"].sort_values("calendar_year")
    region = frames["v_region_kpis"].sort_values("sales", ascending=False)
    subcat = frames["v_subcategory_kpis"].sort_values("profit")
    segment = frames["v_segment_kpis"].sort_values("sales", ascending=False)
    discount = frames["v_discount_impact"].sort_values("discount_band_sort")
    ship = frames["v_ship_mode_kpis"].sort_values("avg_ship_days")
    states = frames["v_state_kpis"].sort_values("profit")
    monthly = frames["v_monthly_kpis"].copy()
    customers = frames["v_customer_summary"]
    products = frames["v_top_products"]

    margin = totals["profit"] / totals["sales"]
    first_year, last_year = yearly.iloc[0], yearly.iloc[-1]
    years = int(last_year["calendar_year"] - first_year["calendar_year"])
    cagr = (float(last_year["sales"]) / float(first_year["sales"])) ** (1 / years) - 1

    loss_subcats = subcat[subcat["profit"] < 0]
    best_region, worst_region = (
        region.sort_values("profit_margin").iloc[-1],
        region.sort_values("profit_margin").iloc[0],
    )
    worst_states = states.head(5)
    avg_discount = totals["avg_discount"]
    no_disc = discount.iloc[0]
    deep_disc = discount.iloc[-1]

    monthly["month_number"] = pd.to_datetime(monthly["month_start"]).dt.month
    seasonality = (
        monthly.groupby("month_number")["sales"].sum()
        / monthly["sales"].sum()
    )
    q4_share = seasonality.loc[[10, 11, 12]].sum()
    peak_month = date(2000, int(seasonality.idxmax()), 1).strftime("%B")

    top_quartile = customers[customers["sales_quartile"] == 1]
    top_quartile_share = top_quartile["sales"].sum() / customers["sales"].sum()
    repeat_share = (customers["orders"] > 1).mean()
    unprofitable_products = (products["profit"] < 0).sum()

    findings = [
        f"**Growth:** sales grew from {money(first_year['sales'])} in "
        f"{int(first_year['calendar_year'])} to {money(last_year['sales'])} in "
        f"{int(last_year['calendar_year'])} ({pct(cagr)} a year on average), "
        f"and profit grew {pct(last_year['profit'] / first_year['profit'] - 1)} "
        "over the same period.",
        f"**Profitability:** the overall profit margin is {pct(margin)}. "
        f"{pct(totals['loss_share'])} of sales lines lose money, costing "
        f"{money(-totals['loss_amount'])} in total.",
        f"**Discounts:** lines with no discount earn a {pct(no_disc['profit_margin'])} "
        f"margin, while discounts of {deep_disc['discount_band']} produce a "
        f"{pct(deep_disc['profit_margin'])} margin, with "
        f"{pct(deep_disc['loss_line_share'])} of those lines losing money.",
        "**Loss-making sub-categories:** "
        + ", ".join(
            f"{r.sub_category} ({money(r.profit)}, avg discount {pct(r.avg_discount)})"
            for r in loss_subcats.itertuples()
        )
        + "." if len(loss_subcats) else "**Loss-making sub-categories:** none.",
        f"**Regions:** {best_region['region']} has the best margin "
        f"({pct(best_region['profit_margin'])}) and {worst_region['region']} "
        f"the weakest ({pct(worst_region['profit_margin'])}). The biggest "
        "losses by state are "
        + ", ".join(
            f"{r.state} ({money(r.profit)}, avg discount {pct(r.avg_discount)})"
            for r in worst_states.itertuples()
        )
        + f", compared with a company-wide average discount of {pct(avg_discount)}.",
        f"**Seasonality:** {pct(q4_share)} of all sales fall in October to "
        f"December, and {peak_month} is the strongest month.",
        f"**Customers:** the top 25% of customers generate "
        f"{pct(top_quartile_share)} of sales, and {pct(repeat_share)} of "
        "customers ordered more than once.",
        f"**Products:** {unprofitable_products:,} of {len(products):,} "
        "products lost money over the whole period (a product is an ID and "
        f"name pair; {int(totals['products']):,} distinct IDs).",
        f"**Shipping:** average time from order to shipment is "
        f"{float(totals['avg_ship_days']):.1f} days, ranging from "
        f"{float(ship.iloc[0]['avg_ship_days']):.1f} ({ship.iloc[0]['ship_mode']}) "
        f"to {float(ship.iloc[-1]['avg_ship_days']):.1f} ({ship.iloc[-1]['ship_mode']}).",
    ]

    recommendations = [
        "Cap discounts at 20% unless a promotion is shown to be profitable: "
        "every band above 20% has a negative margin.",
        "Review pricing, supplier costs and discount policy for the "
        "loss-making sub-categories listed above.",
        "Review discounting in the worst states by profit, where average "
        "discounts are well above the company average.",
        "Plan inventory and marketing around the Q4 peak.",
        "Protect the top customer quartile with retention offers, since it "
        "drives most of the revenue.",
    ]

    sections = [
        "# Retail Sales Insights Report",
        "",
        f"Generated {date.today().isoformat()} from the `reporting` schema "
        "in PostgreSQL. Source: Sample Superstore, orders from "
        f"{totals['first_order']} to {totals['last_order']}.",
        "",
        "## Headline numbers",
        "",
        md_table(
            pd.DataFrame([totals]),
            {
                "Sales": lambda r: money(r["sales"]),
                "Profit": lambda r: money(r["profit"]),
                "Margin": lambda r: pct(margin),
                "Orders": lambda r: f"{int(r['orders']):,}",
                "Customers": lambda r: f"{int(r['customers']):,}",
                "Products": lambda r: f"{int(r['products']):,}",
                "Units": lambda r: f"{int(r['units']):,}",
                "Discount given": lambda r: money(r["discount_amount"]),
            },
        ),
        "",
        "## Key findings",
        "",
        *[f"{i}. {text}" for i, text in enumerate(findings, start=1)],
        "",
        "## Recommendations",
        "",
        *[f"- {text}" for text in recommendations],
        "",
        "## Yearly performance",
        "",
        md_table(
            yearly,
            {
                "Year": lambda r: int(r["calendar_year"]),
                "Sales": lambda r: money(r["sales"]),
                "Profit": lambda r: money(r["profit"]),
                "Margin": lambda r: pct(r["profit_margin"]),
                "Orders": lambda r: f"{int(r['orders']):,}",
                "Avg order value": lambda r: f"${float(r['avg_order_value']):,.2f}",
                "Sales YoY": lambda r: pct(r["sales_yoy_growth"]),
            },
        ),
        "",
        "## Region performance",
        "",
        md_table(
            region,
            {
                "Region": lambda r: r["region"],
                "Sales": lambda r: money(r["sales"]),
                "Profit": lambda r: money(r["profit"]),
                "Margin": lambda r: pct(r["profit_margin"]),
                "Avg discount": lambda r: pct(r["avg_discount"]),
            },
        ),
        "",
        "## Segment performance",
        "",
        md_table(
            segment,
            {
                "Segment": lambda r: r["segment"],
                "Customers": lambda r: f"{int(r['customers']):,}",
                "Sales": lambda r: money(r["sales"]),
                "Profit": lambda r: money(r["profit"]),
                "Margin": lambda r: pct(r["profit_margin"]),
            },
        ),
        "",
        "## Discount impact",
        "",
        md_table(
            discount,
            {
                "Discount band": lambda r: r["discount_band"],
                "Lines": lambda r: f"{int(r['sales_lines']):,}",
                "Sales": lambda r: money(r["sales"]),
                "Profit": lambda r: money(r["profit"]),
                "Margin": lambda r: pct(r["profit_margin"]),
                "Loss-making lines": lambda r: pct(r["loss_line_share"]),
            },
        ),
        "",
        "## Sub-category profitability (worst first)",
        "",
        md_table(
            subcat,
            {
                "Category": lambda r: r["category"],
                "Sub-category": lambda r: r["sub_category"],
                "Sales": lambda r: money(r["sales"]),
                "Profit": lambda r: money(r["profit"]),
                "Margin": lambda r: pct(r["profit_margin"]),
                "Avg discount": lambda r: pct(r["avg_discount"]),
            },
        ),
        "",
        "## Shipping",
        "",
        md_table(
            ship,
            {
                "Ship mode": lambda r: r["ship_mode"],
                "Orders": lambda r: f"{int(r['orders']):,}",
                "Avg days to ship": lambda r: f"{float(r['avg_ship_days']):.1f}",
                "Sales": lambda r: money(r["sales"]),
                "Margin": lambda r: pct(r["profit_margin"]),
            },
        ),
        "",
        "## Top 10 customers by sales",
        "",
        md_table(
            customers.sort_values("sales", ascending=False).head(10),
            {
                "Customer": lambda r: r["customer_name"],
                "Segment": lambda r: r["segment"],
                "Orders": lambda r: int(r["orders"]),
                "Sales": lambda r: money(r["sales"]),
                "Profit": lambda r: money(r["profit"]),
            },
        ),
        "",
        "CSV extracts of every summary view are in `reports/extracts/`.",
        "",
    ]

    report_path = REPORTS_DIR / "sales_insights.md"
    report_path.write_text("\n".join(sections), encoding="utf-8")
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
