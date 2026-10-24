# Retail Sales Analytics Pipeline and Power BI Dashboard

An end-to-end analytics project on the Sample Superstore dataset (9,994
sales lines, 2014 to 2017). PySpark validates and cleans the raw CSV,
PostgreSQL holds a star-schema warehouse with a reporting layer, and
Power BI presents the results.

```
Raw CSV --> PySpark ingest + quality rules --> Parquet (clean / rejected)
        --> PostgreSQL staging --> star schema (analytics)
        --> reporting views --> Power BI dashboard + insights report
```

## Highlights

- Explicit typing and 20+ data quality rules; rejected rows are kept with
  reasons and every source row is reconciled.
- Transactional warehouse load that rolls back if row counts, sales,
  profit or order counts drift from the source.
- Contiguous date dimension, ready for Power BI time intelligence.
- Post-load validation suite and Spark unit tests.
- One-command pipeline with timestamped logs.
- Generated insights report: [`reports/sales_insights.md`](reports/sales_insights.md).

## Key findings

- Sales grew 14.8% a year on average, from $484K (2014) to $733K (2017);
  overall profit margin is 12.5%.
- Every discount band above 20% loses money: lines discounted 41%+ have a
  -77% margin.
- Tables, Bookcases and Supplies are the only loss-making sub-categories.
- Texas, Ohio, Pennsylvania and Illinois lose the most money, with average
  discounts of 32 to 39% against a company average of 16%.
- 38% of sales fall in Q4; the top 25% of customers drive 55% of sales.

## Tech stack

PySpark 4.0, PostgreSQL 17, Docker Compose, psycopg 3, pandas,
SQLAlchemy, pytest, Power BI Desktop.

## Project structure

```
compose.yaml, Dockerfile   Postgres and Spark containers
data/raw/                  Source CSV (not committed)
sql/schema.sql             Warehouse star schema
sql/views.sql              Reporting views for Power BI and analysis
src/quality.py             Typing and data quality rules
src/ingest_sales.py        CSV -> clean and rejected Parquet
src/verify.py              Profile of the cleaned Parquet
src/load_to_postgres.py    Parquet -> staging -> star schema
src/apply_sql.py           Applies SQL files (and the read-only role)
src/validate_warehouse.py  Post-load checks
src/generate_report.py     Insights report and CSV extracts
src/run_pipeline.py        Runs every step in order, logs to logs/
src/inspect_dataset.py     One-off profile of the raw CSV
src/spark_test.py          Spark environment smoke test
tests/                     Unit tests for the quality rules
powerbi/                   DAX measures, theme, and the .pbix file
docs/                      Data model and Power BI build guide
reports/                   Insights report and CSV extracts
```

## Running it

Requirements: Docker Desktop. Power BI Desktop for the dashboard.

1. Download `Sample - Superstore.csv` (for example from Kaggle, "Superstore
   Dataset" by Vivek Chowdhury) and put it in `data/raw/`.
2. Create `.env` from the template and set a password:
   ```
   cp .env.example .env
   ```
3. Start the containers:
   ```
   docker compose up -d --build
   ```
4. Run the tests and the pipeline:
   ```
   docker compose exec spark python -m pytest
   docker compose exec spark python src/run_pipeline.py
   ```
   The run log is written to `logs/pipeline_<timestamp>.log`.
5. Build the dashboard by following
   [`docs/power_bi_guide.md`](docs/power_bi_guide.md).

Individual steps can also be run on their own, for example
`docker compose exec spark python src/load_to_postgres.py`.

## Dashboard

The dashboard has four pages: Executive Overview, Products and Discounts,
Customers and Regions, and Shipping and Trends.

The images below are page mockups rendered from the warehouse data with
matplotlib. They show the layout, visuals and fields for each Power BI page
(see the [build guide](docs/power_bi_guide.md)).

### Executive Overview

![Executive Overview mockup](docs/images/mockups/page1_executive_overview.png)

### Products and Discounts

![Products and Discounts mockup](docs/images/mockups/page2_products_discounts.png)

### Customers and Regions

![Customers and Regions mockup](docs/images/mockups/page3_customers_regions.png)

### Shipping and Trends

![Shipping and Trends mockup](docs/images/mockups/page4_shipping_trends.png)

## Documentation

- [Data model and data quality rules](docs/data_model.md)
- [Power BI build guide](docs/power_bi_guide.md)
- [Insights report](reports/sales_insights.md)
