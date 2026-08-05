-- ===============================
-- Gunpla Dataset - PostgreSQL Schema
-- ===============================

-- One additional change is that we will drop the schema if it already exists, as there was a change in the franchise field to only keep a singular string value
-- So dropping the schema is important to maintain all data rows are consistent with updated dataframe and exported csv rows


DROP SCHEMA IF EXISTS bandai_model CASCADE;
CREATE SCHEMA bandai_model;

-- Dimension Tables

CREATE TABLE bandai_model.dim_grade (
    grade_id SERIAL PRIMARY KEY,
    grade_name TEXT NOT NULL UNIQUE
    -- 'High Grade', 'Master Grade', '30 Minute Missions', etc
    -- Not including gradeless kits
);

CREATE TABLE bandai_model.dim_scale (
    scale_id SERIAL PRIMARY KEY,
    scale_name TEXT NOT NULL UNIQUE
    -- 1/144, 1/100, etc
);

CREATE TABLE bandai_model.dim_franchise (
    franchise_id SERIAL PRIMARY KEY,
    franchise_name TEXT NOT NULL UNIQUE
    -- Mobile Suit Gundam SEED, etc
);

CREATE TABLE bandai_model.dim_exclusivity (
    exclusivity_id SERIAL PRIMARY KEY,
    channel_type TEXT NOT NULL UNIQUE
    CHECK (channel_type IN ('Event', 'Storefront', 'Magazine', 'Campaign', 'Lottery', 'Other'))
    -- keeps exclusivity matched with the type returned from clean.py
);


-- Fact Table

CREATE TABLE bandai_model.fact_kit (
    kit_id SERIAL PRIMARY KEY,
    kit_name TEXT NOT NULL UNIQUE,
    japanese_name TEXT,
    jan_isbn TEXT,
    image_url TEXT,
    release_year SMALLINT,
    price_value NUMERIC(12, 2),
    price_currency CHAR(3) CHECK (price_currency IN ('JPY', 'USD')),
    kit_count SMALLINT,
    run_type TEXT,
    glue_needed BOOLEAN,
    need_paint VARCHAR(50),
    is_exclusive BOOLEAN NOT NULL DEFAULT FALSE,
    grade_id INTEGER REFERENCES bandai_model.dim_grade(grade_id) ON DELETE RESTRICT,
    scale_id INTEGER REFERENCES bandai_model.dim_scale(scale_id) ON DELETE RESTRICT,
    exclusivity_id INTEGER REFERENCES bandai_model.dim_exclusivity(exclusivity_id) ON DELETE RESTRICT,
    franchise_id INTEGER REFERENCES bandai_model.dim_franchise(franchise_id) ON DELETE RESTRICT,
    CONSTRAINT price_value_check CHECK (
        price_value IS NULL OR
        (price_currency = 'JPY' and price_value BETWEEN 50 AND 5000000) OR
        (price_currency = 'USD' and price_value BETWEEN 1 AND 5000)
    ),
    CONSTRAINT release_year_check CHECK (
        release_year IS NULL OR 
        release_year BETWEEN 1980 AND 2027
    )
);


-- Create indexes for foreign key columns

CREATE INDEX idx_fact_kit_grade_id ON bandai_model.fact_kit(grade_id);
CREATE INDEX idx_fact_kit_scale_id ON bandai_model.fact_kit(scale_id);
CREATE INDEX idx_fact_kit_exclusivity_id ON bandai_model.fact_kit(exclusivity_id);
CREATE INDEX idx_fact_kit_franchise_id ON bandai_model.fact_kit(franchise_id);


SELECT relname AS table_name, n_live_tup AS row_count
FROM pg_stat_user_tables WHERE schemaname = 'bandai_model';