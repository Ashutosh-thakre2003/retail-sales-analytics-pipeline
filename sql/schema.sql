
CREATE SCHEMA IF NOT EXISTS analytics;

-- Date dimension. The date key uses YYYYMMDD.
CREATE TABLE IF NOT EXISTS analytics.dim_date (
    date_key       INTEGER PRIMARY KEY,
    full_date      DATE NOT NULL UNIQUE,
    calendar_year  SMALLINT NOT NULL,
    quarter_number SMALLINT NOT NULL,
    month_number   SMALLINT NOT NULL,
    month_name     VARCHAR(12) NOT NULL,
    week_number    SMALLINT NOT NULL,
    day_of_month   SMALLINT NOT NULL,
    day_of_week    SMALLINT NOT NULL,
    day_name       VARCHAR(12) NOT NULL,
    is_weekend     BOOLEAN NOT NULL
);

-- Customer dimension.
CREATE TABLE IF NOT EXISTS analytics.dim_customer (
    customer_key  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id   VARCHAR(30) NOT NULL UNIQUE,
    customer_name VARCHAR(150) NOT NULL,
    segment       VARCHAR(50) NOT NULL
);

-- Product dimension.
CREATE TABLE IF NOT EXISTS analytics.dim_product (
    product_key  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id VARCHAR(40) NOT NULL,
    product_name TEXT NOT NULL,
    category     VARCHAR(80) NOT NULL,
    sub_category VARCHAR(80) NOT NULL,
    UNIQUE (product_id, product_name)
);

-- Geography dimension.
CREATE TABLE IF NOT EXISTS analytics.dim_geography (
    geography_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    country       VARCHAR(100) NOT NULL,
    state         VARCHAR(100) NOT NULL,
    city          VARCHAR(150) NOT NULL,
    postal_code   VARCHAR(20) NOT NULL,
    region        VARCHAR(50) NOT NULL,
    UNIQUE (country, state, city, postal_code, region)
);

-- Shipping mode dimension.
CREATE TABLE IF NOT EXISTS analytics.dim_ship_mode (
    ship_mode_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ship_mode     VARCHAR(50) NOT NULL UNIQUE
);

-- Fact table grain: one record per source sales line (Row ID).
CREATE TABLE IF NOT EXISTS analytics.fact_sales (
    row_id          INTEGER PRIMARY KEY,
    order_id        VARCHAR(30) NOT NULL,
    order_date_key  INTEGER NOT NULL REFERENCES analytics.dim_date(date_key),
    ship_date_key   INTEGER NOT NULL REFERENCES analytics.dim_date(date_key),
    customer_key    BIGINT NOT NULL REFERENCES analytics.dim_customer(customer_key),
    product_key     BIGINT NOT NULL REFERENCES analytics.dim_product(product_key),
    geography_key   BIGINT NOT NULL REFERENCES analytics.dim_geography(geography_key),
    ship_mode_key   BIGINT NOT NULL REFERENCES analytics.dim_ship_mode(ship_mode_key),
    quantity        INTEGER NOT NULL CHECK (quantity > 0),
    sales           NUMERIC(18,4) NOT NULL,
    discount        NUMERIC(9,4) NOT NULL CHECK (discount >= 0 AND discount <= 1),
    profit          NUMERIC(18,4) NOT NULL
);

-- Indexes for common analytical filters and joins.
CREATE INDEX IF NOT EXISTS idx_fact_sales_order_id
    ON analytics.fact_sales(order_id);

CREATE INDEX IF NOT EXISTS idx_fact_sales_order_date
    ON analytics.fact_sales(order_date_key);

CREATE INDEX IF NOT EXISTS idx_fact_sales_ship_date
    ON analytics.fact_sales(ship_date_key);

CREATE INDEX IF NOT EXISTS idx_fact_sales_customer
    ON analytics.fact_sales(customer_key);

CREATE INDEX IF NOT EXISTS idx_fact_sales_product
    ON analytics.fact_sales(product_key);

CREATE INDEX IF NOT EXISTS idx_fact_sales_geography
    ON analytics.fact_sales(geography_key);
