# Data Model and Data Quality

## Layers

| Layer | Location | Contents |
| --- | --- | --- |
| Raw | `data/raw/Sample - Superstore.csv` | Source extract, never modified |
| Clean | `data/processed/sales_cleaned/` (Parquet) | Typed, validated rows |
| Rejected | `data/quality/rejected_rows/` (Parquet) | Rows failing a rule, with `rejection_reason` |
| Staging | `analytics.stg_sales` | Copy of the clean Parquet, overwritten each load |
| Warehouse | `analytics.dim_*`, `analytics.fact_sales` | Star schema ([`sql/schema.sql`](../sql/schema.sql)) |
| Reporting | `reporting.*` views | Power BI source and summary views ([`sql/views.sql`](../sql/views.sql)) |

## Star schema

```
                 dim_date (date_key)
                   |  order_date_key (active)
                   |  ship_date_key  (inactive in Power BI)
dim_customer --- fact_sales --- dim_product
                   |       \
          dim_geography    dim_ship_mode
```

**Fact grain:** one row per source sales line (`Row ID`). An order
(`order_id`) can have several lines.

| Table | Key | Rows | Notes |
| --- | --- | --- | --- |
| `fact_sales` | `row_id` | 9,994 | Sales, profit, quantity, discount |
| `dim_date` | `date_key` (YYYYMMDD) | 1,826 | Contiguous calendar, whole years 2014 to 2018 |
| `dim_customer` | `customer_key` | 793 | Natural key `customer_id` |
| `dim_product` | `product_key` | 1,894 | One row per `product_id` + `product_name` pair (1,862 distinct IDs; some IDs have several names in the source) |
| `dim_geography` | `geography_key` | 632 | Country, region, state, city, postal code |
| `dim_ship_mode` | `ship_mode_key` | 4 | |

Dimension keys are surrogate identity columns. Dimensions are upserted;
the fact table is replaced on each load within a single transaction, which
rolls back if the loaded totals do not match the cleaned Parquet.

### Columns added in the reporting layer

`reporting.fact_sales` adds:

| Column | Definition |
| --- | --- |
| `list_sales` | `sales / (1 - discount)`, the value before discount |
| `discount_amount` | `list_sales - sales` |
| `ship_days` | Ship date minus order date |
| `discount_band` | No discount, 1-20%, 21-40%, 41%+ (`discount_band_sort` for ordering) |
| `is_loss` | `profit < 0` |

`reporting.dim_date` adds `quarter_label`, `year_quarter`, `month_short`,
`year_month` and `month_start`.

### Summary views

`v_sales_enriched` (fact joined to all dimensions), `v_yearly_kpis`,
`v_monthly_kpis`, `v_region_kpis`, `v_state_kpis`, `v_subcategory_kpis`,
`v_segment_kpis`, `v_discount_impact`, `v_ship_mode_kpis`,
`v_customer_summary`, `v_top_products`. These feed
`reports/sales_insights.md` and `reports/extracts/*.csv`.

## Data quality rules

Applied in [`src/quality.py`](../src/quality.py). A row failing any rule
is written to `rejected_rows` with every reason, separated by `; `. No
row is silently dropped: the ingest fails if clean plus rejected does not
equal the source count.

| Rule | Reason code |
| --- | --- |
| Row ID is not an integer | `invalid_row_id` |
| Row ID appears more than once (all copies rejected) | `duplicate_row_id` |
| Order or ship date is not a valid `M/d/yyyy` date | `invalid_order_date`, `invalid_ship_date` |
| Sales, quantity, discount or profit is not numeric | `invalid_sales`, `invalid_quantity`, `invalid_discount`, `invalid_profit` |
| Required text field is blank | `missing_<column>` |
| Sales is negative | `negative_sales` |
| Quantity is zero or negative | `nonpositive_quantity` |
| Discount is outside 0 to 1 | `discount_out_of_range` |
| Ship date is before order date | `ship_before_order` |

Negative profit is valid (a loss-making sale) and is not rejected.

Load-time checks (in [`src/load_to_postgres.py`](../src/load_to_postgres.py)):

- A customer ID must have one name and segment.
- A product ID must have one category and sub-category.
- Loaded rows, sales, profit and order count must equal the Parquet totals.

Post-load checks (in [`src/validate_warehouse.py`](../src/validate_warehouse.py)):
calendar has no gaps and covers every fact date, unique row IDs, no
negative shipping times, no unused dimension rows, the reporting views
lose no rows, and the warehouse reconciles with the Parquet totals.

With the current source file, all 9,994 rows pass every rule.
