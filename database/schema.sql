-- ============================================================================
-- Telecom Customer Churn & Network Analysis Data Warehouse
-- DBMS Target: SQLite 3
-- File: database/schema.sql
-- Description: Reproducible DDL script defining two decoupled Star Schemas:
--              1. Customer Churn Data Mart (FACT_CUSTOMER_CHURN)
--              2. Network Performance Data Mart (FACT_NETWORK_KPI)
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
-- CLEANUP (Drop tables if existing to ensure full reproducibility)
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS FACT_NETWORK_KPI;
DROP TABLE IF EXISTS FACT_CUSTOMER_CHURN;
DROP TABLE IF EXISTS DIM_TIME;
DROP TABLE IF EXISTS DIM_NETWORK_TECH;
DROP TABLE IF EXISTS DIM_REGION;
DROP TABLE IF EXISTS DIM_CELL;
DROP TABLE IF EXISTS DIM_PLAN;
DROP TABLE IF EXISTS DIM_CUSTOMER;

-- ============================================================================
-- MART 1: CUSTOMER CHURN STAR SCHEMA
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Dimension: DIM_CUSTOMER
-- Grain: One row per customer account profile
-- Source: WA_Fn-UseC_-Telco-Customer-Churn.csv
-- ----------------------------------------------------------------------------
CREATE TABLE DIM_CUSTOMER (
    customer_key INTEGER PRIMARY KEY AUTOINCREMENT,
    customerID TEXT NOT NULL UNIQUE,
    gender TEXT NOT NULL CHECK (gender IN ('Male', 'Female')),
    SeniorCitizen INTEGER NOT NULL CHECK (SeniorCitizen IN (0, 1)),
    Partner TEXT NOT NULL CHECK (Partner IN ('Yes', 'No')),
    Dependents TEXT NOT NULL CHECK (Dependents IN ('Yes', 'No')),
    tenure INTEGER NOT NULL CHECK (tenure >= 0)
);

-- ----------------------------------------------------------------------------
-- Dimension: DIM_PLAN
-- Grain: One row per distinct combination of contract, service & billing options
-- Source: WA_Fn-UseC_-Telco-Customer-Churn.csv
-- ----------------------------------------------------------------------------
CREATE TABLE DIM_PLAN (
    plan_key INTEGER PRIMARY KEY AUTOINCREMENT,
    Contract TEXT NOT NULL CHECK (Contract IN ('Month-to-month', 'One year', 'Two year')),
    PhoneService TEXT NOT NULL CHECK (PhoneService IN ('Yes', 'No')),
    MultipleLines TEXT NOT NULL CHECK (MultipleLines IN ('Yes', 'No', 'No phone service')),
    InternetService TEXT NOT NULL CHECK (InternetService IN ('DSL', 'Fiber optic', 'No')),
    OnlineSecurity TEXT NOT NULL CHECK (OnlineSecurity IN ('Yes', 'No', 'No internet service')),
    OnlineBackup TEXT NOT NULL CHECK (OnlineBackup IN ('Yes', 'No', 'No internet service')),
    DeviceProtection TEXT NOT NULL CHECK (DeviceProtection IN ('Yes', 'No', 'No internet service')),
    TechSupport TEXT NOT NULL CHECK (TechSupport IN ('Yes', 'No', 'No internet service')),
    StreamingTV TEXT NOT NULL CHECK (StreamingTV IN ('Yes', 'No', 'No internet service')),
    StreamingMovies TEXT NOT NULL CHECK (StreamingMovies IN ('Yes', 'No', 'No internet service')),
    PaperlessBilling TEXT NOT NULL CHECK (PaperlessBilling IN ('Yes', 'No')),
    PaymentMethod TEXT NOT NULL CHECK (PaymentMethod IN (
        'Electronic check',
        'Mailed check',
        'Bank transfer (automatic)',
        'Credit card (automatic)'
    )),
    UNIQUE (
        Contract, PhoneService, MultipleLines, InternetService,
        OnlineSecurity, OnlineBackup, DeviceProtection, TechSupport,
        StreamingTV, StreamingMovies, PaperlessBilling, PaymentMethod
    )
);

-- ----------------------------------------------------------------------------
-- Fact Table: FACT_CUSTOMER_CHURN
-- Grain: One row per customer subscription / customer record from source CSV
-- Analytical/Time Strategy:
--   The source Telco churn CSV provides no event timestamps or transaction dates.
--   Per strict DWDM rules, no event date is fabricated. This fact table functions
--   as a customer lifecycle / subscription snapshot table.
-- Source: WA_Fn-UseC_-Telco-Customer-Churn.csv
-- ----------------------------------------------------------------------------
CREATE TABLE FACT_CUSTOMER_CHURN (
    customer_churn_key INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_key INTEGER NOT NULL,
    plan_key INTEGER NOT NULL,
    monthly_charges REAL NOT NULL CHECK (monthly_charges >= 0),
    total_charges REAL CHECK (total_charges >= 0),
    churn_flag INTEGER NOT NULL CHECK (churn_flag IN (0, 1)),
    customer_count INTEGER NOT NULL DEFAULT 1 CHECK (customer_count = 1),
    FOREIGN KEY (customer_key) REFERENCES DIM_CUSTOMER(customer_key) ON DELETE RESTRICT,
    FOREIGN KEY (plan_key) REFERENCES DIM_PLAN(plan_key) ON DELETE RESTRICT
);

-- Indexes for Customer Churn Mart
CREATE INDEX idx_fact_cust_churn_cust_key ON FACT_CUSTOMER_CHURN(customer_key);
CREATE INDEX idx_fact_cust_churn_plan_key ON FACT_CUSTOMER_CHURN(plan_key);
CREATE INDEX idx_fact_cust_churn_flag ON FACT_CUSTOMER_CHURN(churn_flag);
CREATE INDEX idx_dim_cust_customerID ON DIM_CUSTOMER(customerID);
CREATE INDEX idx_dim_plan_contract ON DIM_PLAN(Contract);
CREATE INDEX idx_dim_plan_internet ON DIM_PLAN(InternetService);

-- ============================================================================
-- MART 2: NETWORK PERFORMANCE STAR SCHEMA
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Dimension: DIM_CELL
-- Grain: One row per physical cell site (120 unique cells in source data)
-- Source: network_kpi_data.csv (cell_id)
-- ----------------------------------------------------------------------------
CREATE TABLE DIM_CELL (
    cell_key INTEGER PRIMARY KEY AUTOINCREMENT,
    cell_id TEXT NOT NULL UNIQUE
);

-- ----------------------------------------------------------------------------
-- Dimension: DIM_REGION
-- Grain: One row per geographic network region (5 regions in source data)
-- Source: network_kpi_data.csv (region)
-- ----------------------------------------------------------------------------
CREATE TABLE DIM_REGION (
    region_key INTEGER PRIMARY KEY AUTOINCREMENT,
    region_name TEXT NOT NULL UNIQUE CHECK (region_name IN ('Central', 'East', 'North', 'South', 'West'))
);

-- ----------------------------------------------------------------------------
-- Dimension: DIM_NETWORK_TECH
-- Grain: One row per radio access technology (2 technologies in source data)
-- Source: network_kpi_data.csv (technology)
-- ----------------------------------------------------------------------------
CREATE TABLE DIM_NETWORK_TECH (
    technology_key INTEGER PRIMARY KEY AUTOINCREMENT,
    technology_name TEXT NOT NULL UNIQUE CHECK (technology_name IN ('LTE', '5G'))
);

-- ----------------------------------------------------------------------------
-- Dimension: DIM_TIME
-- Grain: One row per discrete 1-minute telemetry interval (30 minutes in source)
-- Source: network_kpi_data.csv (timestamp)
-- ----------------------------------------------------------------------------
CREATE TABLE DIM_TIME (
    time_key INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL UNIQUE,
    date TEXT NOT NULL,
    hour INTEGER NOT NULL CHECK (hour BETWEEN 0 AND 23),
    minute INTEGER NOT NULL CHECK (minute BETWEEN 0 AND 59),
    day INTEGER NOT NULL CHECK (day BETWEEN 1 AND 31),
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    quarter INTEGER NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    year INTEGER NOT NULL CHECK (year >= 2000)
);

-- ----------------------------------------------------------------------------
-- Fact Table: FACT_NETWORK_KPI
-- Grain: One row per actual cell telemetry observation (1 cell reading per min)
-- Source: network_kpi_data.csv
-- ----------------------------------------------------------------------------
CREATE TABLE FACT_NETWORK_KPI (
    network_kpi_key INTEGER PRIMARY KEY AUTOINCREMENT,
    cell_key INTEGER NOT NULL,
    region_key INTEGER NOT NULL,
    technology_key INTEGER NOT NULL,
    time_key INTEGER NOT NULL,
    latency_ms REAL NOT NULL CHECK (latency_ms >= 0),
    throughput_mbps REAL NOT NULL CHECK (throughput_mbps >= 0),
    packet_loss_pct REAL NOT NULL CHECK (packet_loss_pct BETWEEN 0 AND 100),
    call_drop_rate_pct REAL NOT NULL CHECK (call_drop_rate_pct BETWEEN 0 AND 100),
    signal_strength_dbm REAL NOT NULL,
    handover_success_pct REAL NOT NULL CHECK (handover_success_pct BETWEEN 0 AND 100),
    active_connections INTEGER NOT NULL CHECK (active_connections >= 0),
    reading_count INTEGER NOT NULL DEFAULT 1 CHECK (reading_count = 1),
    FOREIGN KEY (cell_key) REFERENCES DIM_CELL(cell_key) ON DELETE RESTRICT,
    FOREIGN KEY (region_key) REFERENCES DIM_REGION(region_key) ON DELETE RESTRICT,
    FOREIGN KEY (technology_key) REFERENCES DIM_NETWORK_TECH(technology_key) ON DELETE RESTRICT,
    FOREIGN KEY (time_key) REFERENCES DIM_TIME(time_key) ON DELETE RESTRICT
);

-- Indexes for Network Performance Mart
CREATE INDEX idx_fact_net_kpi_cell_key ON FACT_NETWORK_KPI(cell_key);
CREATE INDEX idx_fact_net_kpi_region_key ON FACT_NETWORK_KPI(region_key);
CREATE INDEX idx_fact_net_kpi_tech_key ON FACT_NETWORK_KPI(technology_key);
CREATE INDEX idx_fact_net_kpi_time_key ON FACT_NETWORK_KPI(time_key);
CREATE INDEX idx_fact_net_kpi_composite ON FACT_NETWORK_KPI(cell_key, time_key);
CREATE INDEX idx_dim_cell_id ON DIM_CELL(cell_id);
CREATE INDEX idx_dim_region_name ON DIM_REGION(region_name);
CREATE INDEX idx_dim_tech_name ON DIM_NETWORK_TECH(technology_name);
CREATE INDEX idx_dim_time_timestamp ON DIM_TIME(timestamp);
CREATE INDEX idx_dim_time_date_hour ON DIM_TIME(date, hour);
