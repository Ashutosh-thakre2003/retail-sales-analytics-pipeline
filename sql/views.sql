
-- Reporting layer consumed by Power BI and the insights report.
-- The schema is rebuilt on every run so view definitions never drift.
DROP SCHEMA IF EXISTS reporting CASCADE;
CREATE SCHEMA reporting;

-- ---------------------------------------------------------------------------
-- Star schema views (import these into Power BI)
-- ---------------------------------------------------------------------------

CREATE VIEW reporting.dim_date AS
SELECT
    d.date_key,
    d.full_date,
    d.calendar_year,
    d.quarter_number,
    'Q' || d.quarter_number                          AS quarter_label,
    d.calendar_year || '-Q' || d.quarter_number      AS year_quarter,
    d.month_number,
    d.month_name,
    LEFT(d.month_name, 3)                            AS month_short,
    TO_CHAR(d.full_date, 'YYYY-MM')                  AS year_month,
    DATE_TRUNC('month', d.full_date)::DATE           AS month_start,
    d.week_number,
    d.day_of_month,
    d.day_of_week,
    d.day_name,
    d.is_weekend
FROM analytics.dim_date d;

CREATE VIEW reporting.dim_customer AS
SELECT customer_key, customer_id, customer_name, segment
FROM analytics.dim_customer;

CREATE VIEW reporting.dim_product AS
SELECT product_key, product_id, product_name, category, sub_category
FROM analytics.dim_product;

CREATE VIEW reporting.dim_geography AS
SELECT
    geography_key,
    country,
    region,
    state,
    city,
    postal_code,
    city || ', ' || state || ', ' || country AS city_label
FROM analytics.dim_geography;

CREATE VIEW reporting.dim_ship_mode AS
SELECT
    ship_mode_key,
    ship_mode,
    CASE ship_mode
        WHEN 'Same Day'       THEN 1
        WHEN 'First Class'    THEN 2
        WHEN 'Second Class'   THEN 3
        WHEN 'Standard Class' THEN 4
        ELSE 99
    END AS ship_mode_sort
FROM analytics.dim_ship_mode;

CREATE VIEW reporting.fact_sales AS
SELECT
    f.row_id,
    f.order_id,
    f.order_date_key,
    f.ship_date_key,
    f.customer_key,
    f.product_key,
    f.geography_key,
    f.ship_mode_key,
    f.quantity,
    f.sales,
    f.discount,
    f.profit,
    -- Superstore sales are net of discount; reconstruct the list value.
    ROUND(f.sales / NULLIF(1 - f.discount, 0), 4)            AS list_sales,
    ROUND(f.sales / NULLIF(1 - f.discount, 0) - f.sales, 4)  AS discount_amount,
    (sd.full_date - od.full_date)                            AS ship_days,
    CASE
        WHEN f.discount = 0    THEN 'No discount'
        WHEN f.discount <= 0.2 THEN '1-20%'
        WHEN f.discount <= 0.4 THEN '21-40%'
        ELSE '41%+'
    END AS discount_band,
    CASE
        WHEN f.discount = 0    THEN 1
        WHEN f.discount <= 0.2 THEN 2
        WHEN f.discount <= 0.4 THEN 3
        ELSE 4
    END AS discount_band_sort,
    (f.profit < 0) AS is_loss
FROM analytics.fact_sales f
JOIN analytics.dim_date od ON od.date_key = f.order_date_key
JOIN analytics.dim_date sd ON sd.date_key = f.ship_date_key;

-- ---------------------------------------------------------------------------
-- Analytical summary views (used by the insights report and ad hoc SQL)
-- ---------------------------------------------------------------------------

CREATE VIEW reporting.v_sales_enriched AS
SELECT
    f.*,
    d.full_date AS order_date,
    d.calendar_year,
    d.month_start,
    c.customer_id,
    c.customer_name,
    c.segment,
    p.product_id,
    p.product_name,
    p.category,
    p.sub_category,
    g.region,
    g.state,
    g.city,
    sm.ship_mode
FROM reporting.fact_sales f
JOIN reporting.dim_date d       ON d.date_key = f.order_date_key
JOIN reporting.dim_customer c   ON c.customer_key = f.customer_key
JOIN reporting.dim_product p    ON p.product_key = f.product_key
JOIN reporting.dim_geography g  ON g.geography_key = f.geography_key
JOIN reporting.dim_ship_mode sm ON sm.ship_mode_key = f.ship_mode_key;

CREATE VIEW reporting.v_yearly_kpis AS
WITH y AS (
    SELECT
        calendar_year,
        COUNT(DISTINCT order_id)    AS orders,
        COUNT(DISTINCT customer_id) AS customers,
        SUM(quantity)               AS units,
        SUM(sales)                  AS sales,
        SUM(profit)                 AS profit
    FROM reporting.v_sales_enriched
    GROUP BY calendar_year
)
SELECT
    calendar_year,
    orders,
    customers,
    units,
    ROUND(sales, 2)                                   AS sales,
    ROUND(profit, 2)                                  AS profit,
    ROUND(profit / NULLIF(sales, 0), 4)               AS profit_margin,
    ROUND(sales / NULLIF(orders, 0), 2)               AS avg_order_value,
    ROUND(sales / NULLIF(LAG(sales) OVER w, 0) - 1, 4) AS sales_yoy_growth,
    ROUND(profit / NULLIF(LAG(profit) OVER w, 0) - 1, 4) AS profit_yoy_growth
FROM y
WINDOW w AS (ORDER BY calendar_year);

CREATE VIEW reporting.v_monthly_kpis AS
SELECT
    month_start,
    COUNT(DISTINCT order_id)                      AS orders,
    COUNT(DISTINCT customer_id)                   AS customers,
    SUM(quantity)                                 AS units,
    ROUND(SUM(sales), 2)                          AS sales,
    ROUND(SUM(profit), 2)                         AS profit,
    ROUND(SUM(profit) / NULLIF(SUM(sales), 0), 4) AS profit_margin,
    ROUND(AVG(discount), 4)                       AS avg_discount
FROM reporting.v_sales_enriched
GROUP BY month_start;

CREATE VIEW reporting.v_region_kpis AS
SELECT
    region,
    COUNT(DISTINCT order_id)                      AS orders,
    COUNT(DISTINCT customer_id)                   AS customers,
    ROUND(SUM(sales), 2)                          AS sales,
    ROUND(SUM(profit), 2)                         AS profit,
    ROUND(SUM(profit) / NULLIF(SUM(sales), 0), 4) AS profit_margin,
    ROUND(AVG(discount), 4)                       AS avg_discount
FROM reporting.v_sales_enriched
GROUP BY region;

CREATE VIEW reporting.v_state_kpis AS
SELECT
    region,
    state,
    COUNT(DISTINCT order_id)                      AS orders,
    ROUND(SUM(sales), 2)                          AS sales,
    ROUND(SUM(profit), 2)                         AS profit,
    ROUND(SUM(profit) / NULLIF(SUM(sales), 0), 4) AS profit_margin,
    ROUND(AVG(discount), 4)                       AS avg_discount
FROM reporting.v_sales_enriched
GROUP BY region, state;

CREATE VIEW reporting.v_subcategory_kpis AS
SELECT
    category,
    sub_category,
    COUNT(*)                                      AS sales_lines,
    SUM(quantity)                                 AS units,
    ROUND(SUM(sales), 2)                          AS sales,
    ROUND(SUM(profit), 2)                         AS profit,
    ROUND(SUM(profit) / NULLIF(SUM(sales), 0), 4) AS profit_margin,
    ROUND(AVG(discount), 4)                       AS avg_discount,
    ROUND(AVG(is_loss::INT), 4)                   AS loss_line_share
FROM reporting.v_sales_enriched
GROUP BY category, sub_category;

CREATE VIEW reporting.v_segment_kpis AS
SELECT
    segment,
    COUNT(DISTINCT customer_id)                   AS customers,
    COUNT(DISTINCT order_id)                      AS orders,
    ROUND(SUM(sales), 2)                          AS sales,
    ROUND(SUM(profit), 2)                         AS profit,
    ROUND(SUM(profit) / NULLIF(SUM(sales), 0), 4) AS profit_margin,
    ROUND(SUM(sales) / NULLIF(COUNT(DISTINCT order_id), 0), 2) AS avg_order_value
FROM reporting.v_sales_enriched
GROUP BY segment;

CREATE VIEW reporting.v_discount_impact AS
SELECT
    discount_band,
    discount_band_sort,
    COUNT(*)                                      AS sales_lines,
    ROUND(SUM(sales), 2)                          AS sales,
    ROUND(SUM(profit), 2)                         AS profit,
    ROUND(SUM(profit) / NULLIF(SUM(sales), 0), 4) AS profit_margin,
    ROUND(AVG(is_loss::INT), 4)                   AS loss_line_share
FROM reporting.v_sales_enriched
GROUP BY discount_band, discount_band_sort;

CREATE VIEW reporting.v_ship_mode_kpis AS
SELECT
    ship_mode,
    COUNT(*)                                      AS sales_lines,
    COUNT(DISTINCT order_id)                      AS orders,
    ROUND(AVG(ship_days), 2)                      AS avg_ship_days,
    ROUND(SUM(sales), 2)                          AS sales,
    ROUND(SUM(profit), 2)                         AS profit,
    ROUND(SUM(profit) / NULLIF(SUM(sales), 0), 4) AS profit_margin
FROM reporting.v_sales_enriched
GROUP BY ship_mode;

-- Customer-level summary with recency measured against the latest order
-- in the dataset (the extract is historical, so CURRENT_DATE is not used).
CREATE VIEW reporting.v_customer_summary AS
WITH c AS (
    SELECT
        customer_id,
        customer_name,
        segment,
        MIN(order_date)          AS first_order_date,
        MAX(order_date)          AS last_order_date,
        COUNT(DISTINCT order_id) AS orders,
        SUM(sales)               AS sales,
        SUM(profit)              AS profit
    FROM reporting.v_sales_enriched
    GROUP BY customer_id, customer_name, segment
)
SELECT
    c.customer_id,
    c.customer_name,
    c.segment,
    c.first_order_date,
    c.last_order_date,
    (SELECT MAX(order_date) FROM reporting.v_sales_enriched)
        - c.last_order_date                       AS recency_days,
    c.orders,
    ROUND(c.sales, 2)                             AS sales,
    ROUND(c.profit, 2)                            AS profit,
    ROUND(c.profit / NULLIF(c.sales, 0), 4)       AS profit_margin,
    NTILE(4) OVER (ORDER BY c.sales DESC)         AS sales_quartile
FROM c;

CREATE VIEW reporting.v_top_products AS
SELECT
    category,
    sub_category,
    product_id,
    product_name,
    SUM(quantity)                                 AS units,
    ROUND(SUM(sales), 2)                          AS sales,
    ROUND(SUM(profit), 2)                         AS profit,
    ROUND(SUM(profit) / NULLIF(SUM(sales), 0), 4) AS profit_margin
FROM reporting.v_sales_enriched
GROUP BY category, sub_category, product_id, product_name;
