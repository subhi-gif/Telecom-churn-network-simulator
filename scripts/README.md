# ETL Scripts Documentation

## Overview
This directory contains the automated Extract, Transform, and Load (ETL) pipeline scripts for the **Telecom Customer Churn & Network Analysis** Data Warehouse.

## Files
- **`etl_customer.py`**: Extracts `data/WA_Fn-UseC_-Telco-Customer-Churn.csv`, validates data quality, standardizes values, imputes 11 blank `TotalCharges` records to `0.00`, derives `tenure_band`, maps `Churn` to binary `0/1`, loads `DIM_CUSTOMER` and `DIM_PLAN`, and populates `FACT_CUSTOMER_CHURN`.
- **`etl_network.py`**: Extracts `data/network_kpi_data.csv`, validates telemetry metrics, parses timestamps to derive date/time attributes, loads `DIM_CELL`, `DIM_REGION`, `DIM_NETWORK_TECH`, and `DIM_TIME`, and populates `FACT_NETWORK_KPI`.
- **`run_etl.py`**: Master orchestrator that can rebuild the database from scratch (`--reset`), run both ETL modules sequentially, and execute post-ETL integrity checks and aggregate reconciliation.

## Usage

### Run End-to-End Pipeline with Fresh Database Reset:
```powershell
python scripts/run_etl.py --reset
```

### Run Customer ETL Independently:
```powershell
python scripts/etl_customer.py
```

### Run Network ETL Independently:
```powershell
python scripts/etl_network.py
```
