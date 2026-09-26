# Telecom Customer Churn & Network Analysis — Data Warehouse Documentation

## 1. Warehouse Purpose
This Data Warehouse is implemented for an academic B.Tech Data Warehousing & Data Mining (DWDM) project titled **"Telecom Customer Churn & Network Analysis"**. 

Its primary objective is to structure, clean, and store enterprise telecom data in a dimensional Kimball Star Schema format to enable:
- High-performance Online Analytical Processing (OLAP) slicing, dicing, and drill-downs.
- Downstream Data Mining workflows (e.g., classification modeling for churn prediction, time-series analysis for network quality degradation).
- Reliable reporting and executive simulation dashboards.

The database is built on **SQLite 3** (`database/warehouse.db`) and is 100% reproducible from the DDL script in `database/schema.sql`.

---

## 2. Architecture Overview: Two Independent Star Schemas
The source datasets represent two distinct operational domains with no shared keys:
1. **Customer Domain (`WA_Fn-UseC_-Telco-Customer-Churn.csv`)**: Customer account lifecycle, commercial plans, subscribed services, and churn status.
2. **Network Domain (`network_kpi_data.csv`)**: High-frequency cell-tower telemetry capturing Quality of Service (QoS) metrics.

To maintain strict data integrity without fabricating synthetic links, the warehouse is architected as **Two Independent Data Marts**.

---

## 3. Mart 1: Customer Churn Mart

### Fact Table: `FACT_CUSTOMER_CHURN`
- **Grain:** One row per customer account / subscription record from the source Telco dataset.
- **Primary Key:** `customer_churn_key` (Surrogate integer, AUTOINCREMENT)
- **Foreign Keys:**
  - `customer_key` $\rightarrow$ `DIM_CUSTOMER(customer_key)`
  - `plan_key` $\rightarrow$ `DIM_PLAN(plan_key)`
- **Measures:**
  - `monthly_charges` (`REAL`): Recurring monthly bill amount.
  - `total_charges` (`REAL`): Cumulative billed amount (cleaned numeric; `0.00` for month-0 customers).
  - `churn_flag` (`INTEGER`): Binary indicator (`1` = Churned, `0` = Retained) for additive rate calculations.
  - `customer_count` (`INTEGER`): Additive unit constant (`1`) for cohort aggregations.

### Dimension Tables:
1. **`DIM_CUSTOMER`**:
   - **Grain:** One row per customer profile.
   - **Primary Key:** `customer_key` (Surrogate integer)
   - **Natural Key:** `customerID` (`TEXT UNIQUE`)
   - **Attributes:** `gender`, `SeniorCitizen`, `Partner`, `Dependents`, `tenure`.
2. **`DIM_PLAN`**:
   - **Grain:** One row per unique commercial plan and service subscription bundle.
   - **Primary Key:** `plan_key` (Surrogate integer)
   - **Attributes:** `Contract`, `PhoneService`, `MultipleLines`, `InternetService`, `OnlineSecurity`, `OnlineBackup`, `DeviceProtection`, `TechSupport`, `StreamingTV`, `StreamingMovies`, `PaperlessBilling`, `PaymentMethod`.

---

## 4. Mart 2: Network Performance Mart

### Fact Table: `FACT_NETWORK_KPI`
- **Grain:** One row per cell tower per discrete 1-minute telemetry observation.
- **Primary Key:** `network_kpi_key` (Surrogate integer, AUTOINCREMENT)
- **Foreign Keys:**
  - `cell_key` $\rightarrow$ `DIM_CELL(cell_key)`
  - `region_key` $\rightarrow$ `DIM_REGION(region_key)`
  - `technology_key` $\rightarrow$ `DIM_NETWORK_TECH(technology_key)`
  - `time_key` $\rightarrow$ `DIM_TIME(time_key)`
- **Measures:**
  - `latency_ms` (`REAL`): Round-trip delay in milliseconds.
  - `throughput_mbps` (`REAL`): Data transfer rate in Mbps.
  - `packet_loss_pct` (`REAL`): Percentage of dropped packets.
  - `call_drop_rate_pct` (`REAL`): Percentage of dropped calls.
  - `signal_strength_dbm` (`REAL`): Received power in dBm.
  - `handover_success_pct` (`REAL`): Handover completion percentage.
  - `active_connections` (`INTEGER`): Concurrent active sessions.
  - `reading_count` (`INTEGER`): Additive unit constant (`1`) for telemetry sample counts.

### Dimension Tables:
1. **`DIM_CELL`**:
   - **Grain:** One row per physical cell site (120 unique cells: `Cell_0001` - `Cell_0120`).
   - **Primary Key:** `cell_key` (Surrogate integer)
   - **Natural Key:** `cell_id` (`TEXT UNIQUE`)
2. **`DIM_REGION`**:
   - **Grain:** One row per geographic region (5 regions: Central, East, North, South, West).
   - **Primary Key:** `region_key` (Surrogate integer)
   - **Natural Key / Name:** `region_name` (`TEXT UNIQUE`)
3. **`DIM_NETWORK_TECH`**:
   - **Grain:** One row per radio access technology (2 technologies: LTE, 5G).
   - **Primary Key:** `technology_key` (Surrogate integer)
   - **Natural Key / Name:** `technology_name` (`TEXT UNIQUE`)
4. **`DIM_TIME`**:
   - **Grain:** One row per discrete 1-minute telemetry interval (30 records: 14:00 to 14:29).
   - **Primary Key:** `time_key` (Surrogate integer)
   - **Attributes:** `timestamp`, `date`, `hour`, `minute`, `day`, `month`, `quarter`, `year`.

---

## 5. Summary of Fact and Dimension Grains

| Table Name | Table Type | Entity Grain | Source Record Count |
| :--- | :--- | :--- | :---: |
| `FACT_CUSTOMER_CHURN` | Fact | One row per customer subscription | 7,043 |
| `DIM_CUSTOMER` | Dimension | One row per customer demographic profile | 7,043 |
| `DIM_PLAN` | Dimension | One row per distinct service plan combination | Up to 7,043 (de-duplicated) |
| `FACT_NETWORK_KPI` | Fact | One row per cell site per discrete minute | 3,600 (120 cells $\times$ 30 mins) |
| `DIM_CELL` | Dimension | One row per physical cell tower site | 120 |
| `DIM_REGION` | Dimension | One row per operational geographic region | 5 |
| `DIM_NETWORK_TECH` | Dimension | One row per radio access network technology | 2 |
| `DIM_TIME` | Dimension | One row per discrete minute interval | 30 |

---

## 6. Primary and Foreign Keys Reference

| Table | Primary Key | Foreign Keys & Targets |
| :--- | :--- | :--- |
| `DIM_CUSTOMER` | `customer_key` | None |
| `DIM_PLAN` | `plan_key` | None |
| `FACT_CUSTOMER_CHURN` | `customer_churn_key` | `customer_key` $\rightarrow$ `DIM_CUSTOMER(customer_key)`<br>`plan_key` $\rightarrow$ `DIM_PLAN(plan_key)` |
| `DIM_CELL` | `cell_key` | None |
| `DIM_REGION` | `region_key` | None |
| `DIM_NETWORK_TECH` | `technology_key` | None |
| `DIM_TIME` | `time_key` | None |
| `FACT_NETWORK_KPI` | `network_kpi_key` | `cell_key` $\rightarrow$ `DIM_CELL(cell_key)`<br>`region_key` $\rightarrow$ `DIM_REGION(region_key)`<br>`technology_key` $\rightarrow$ `DIM_NETWORK_TECH(technology_key)`<br>`time_key` $\rightarrow$ `DIM_TIME(time_key)` |

---

## 7. Analytical Measures Summary

### Customer Churn Mart Measures:
- **`monthly_charges`**: Semi-additive decimal representing the current billing rate per subscriber.
- **`total_charges`**: Fully additive decimal representing total historical revenue collected.
- **`churn_flag`**: Additive binary indicator (`1` or `0`). When summed and divided by `SUM(customer_count)`, it directly yields the Churn Rate (%).
- **`customer_count`**: Additive integer constant (`1`) enabling multi-dimensional roll-up counts.

### Network Performance Mart Measures:
- **`latency_ms`**: Additive across samples for average/max calculation (`AVG(latency_ms)`).
- **`throughput_mbps`**: Additive across cells for bandwidth consumption; averageable for speed profiling.
- **`packet_loss_pct`**: Semi-additive percentage measure.
- **`call_drop_rate_pct`**: Semi-additive percentage measure.
- **`signal_strength_dbm`**: Non-additive decibel measure; requires average or threshold grouping.
- **`handover_success_pct`**: Semi-additive reliability percentage.
- **`active_connections`**: Additive across cells at any single timestamp; averageable across time.
- **`reading_count`**: Additive integer constant (`1`) for telemetry sample volume counts.

---

## 8. Source Limitations & Design Rationale

### Why There Is No Bridge Table
A bridge table (such as `Customer_Cell_Assignment`) is used in dimensional modeling only when a genuine relationship exists between entities (e.g., many-to-many relationships or multi-valued dimensions). 

In this project's raw datasets:
- **Zero common attributes exist** between the customer and network CSV files ($\text{Columns}(\text{Customer}) \cap \text{Columns}(\text{Network}) = \emptyset$).
- There is no customer ID in the network logs.
- There is no tower ID, cell ID, or region in the customer data.
- Introducing a bridge table without real relational data would constitute fabricated data, violating core DWDM principles.

### Why The Customer Churn Mart Has No Event Time Dimension
- The IBM Telco Customer Churn dataset is completely static and cross-sectional.
- It contains only cumulative `tenure` (0 to 72 months) and has **no calendar dates, transaction timestamps, or churn event dates**.
- Fabricating event dates would introduce artificial bias into OLAP cubes and temporal mining models. Therefore, `FACT_CUSTOMER_CHURN` is modeled strictly as a **Customer Lifecycle Snapshot Fact Table** without an artificial time foreign key.

### Why The Two Marts Remain Independent
- **Independent Analytical Subjects:** The Customer Mart supports business and financial intelligence (churn drivers, contract stickiness, revenue per user). The Network Mart supports infrastructure and engineering intelligence (cell congestion, packet loss hotspots, handover failures).
- **Decoupled Enterprise Warehouse:** In enterprise data warehousing, different business processes frequently have distinct dimensional models that exist side-by-side. Both marts are housed within the same analytical database (`warehouse.db`), allowing independent querying and executive-level side-by-side dashboarding.

---

## 9. ETL Architecture & Execution Pipeline

The ETL subsystem (`scripts/`) executes a staged Kimball data pipeline:
```
EXTRACT  ──────►  STAGING  ──────►  TRANSFORM  ──────►  VALIDATE  ──────►  DIMENSION LOAD  ──────►  FACT LOAD
```

### 1. Extract Process
- Raw CSV files are read read-only without modifying the original source files (`data/WA_Fn-UseC_-Telco-Customer-Churn.csv` and `data/network_kpi_data.csv`).
- Data is loaded into Pandas DataFrames with explicit data-type casting safeguards.

### 2. Transform Process & Data-Quality Handling
- **`TotalCharges` Cleaning:** The 11 source records with whitespace `" "` are imputed to `0.00` because all 11 records have `tenure == 0` (new subscribers who joined during the current billing period).
- **`Churn` Mapping:** Converted from text strings `'Yes'`/`'No'` to integer binary flags `1`/`0`.
- **`tenure_band` Derivation:** Customers are segmented into analytical tenure cohorts:
  - `0-12 months` (2,186 customers)
  - `13-24 months` (1,024 customers)
  - `25-48 months` (1,594 customers)
  - `49-72 months` (2,239 customers)
- **Timestamp Decomposition (Network):** High-resolution timestamps are parsed to derive temporal attributes: `date`, `hour`, `minute`, `day`, `month`, `quarter`, and `year`.

### 3. Source-to-Target Mappings

#### Customer Mart Mapping:
| Source Column (`WA_Fn-UseC_-Telco...`) | Target Table | Target Column | Transformation / Rule |
| :--- | :--- | :--- | :--- |
| `customerID` | `DIM_CUSTOMER` | `customerID` | Preserved as natural unique business key |
| `gender`, `SeniorCitizen`, `Partner`, `Dependents`, `tenure` | `DIM_CUSTOMER` | Same name | Direct load |
| `Contract`, `PhoneService`, `MultipleLines`, `InternetService`, `OnlineSecurity`, `OnlineBackup`, `DeviceProtection`, `TechSupport`, `StreamingTV`, `StreamingMovies`, `PaperlessBilling`, `PaymentMethod` | `DIM_PLAN` | Same name | De-duplicated dimension members |
| Generated | `FACT_CUSTOMER_CHURN` | `customer_key` | Foreign key resolved from `DIM_CUSTOMER` |
| Generated | `FACT_CUSTOMER_CHURN` | `plan_key` | Foreign key resolved from `DIM_PLAN` |
| `MonthlyCharges` | `FACT_CUSTOMER_CHURN` | `monthly_charges` | Cast to REAL |
| `TotalCharges` | `FACT_CUSTOMER_CHURN` | `total_charges` | Whitespace $\rightarrow 0.00$, cast to REAL |
| `Churn` | `FACT_CUSTOMER_CHURN` | `churn_flag` | 'Yes' $\rightarrow 1$, 'No' $\rightarrow 0$ |
| Constant | `FACT_CUSTOMER_CHURN` | `customer_count` | Default 1 |

#### Network Mart Mapping:
| Source Column (`network_kpi_data.csv`) | Target Table | Target Column | Transformation / Rule |
| :--- | :--- | :--- | :--- |
| `cell_id` | `DIM_CELL` | `cell_id` | Distinct unique cells (120) |
| `region` | `DIM_REGION` | `region_name` | Distinct unique regions (5) |
| `technology` | `DIM_NETWORK_TECH` | `technology_name` | Distinct unique technologies (2) |
| `timestamp` | `DIM_TIME` | `timestamp`, `date`, `hour`, `minute`, `day`, `month`, `quarter`, `year` | Decomposed datetime attributes (30 minutes) |
| `cell_id` | `FACT_NETWORK_KPI` | `cell_key` | Foreign key resolved from `DIM_CELL` |
| `region` | `FACT_NETWORK_KPI` | `region_key` | Foreign key resolved from `DIM_REGION` |
| `technology` | `FACT_NETWORK_KPI` | `technology_key` | Foreign key resolved from `DIM_NETWORK_TECH` |
| `timestamp` | `FACT_NETWORK_KPI` | `time_key` | Foreign key resolved from `DIM_TIME` |
| Performance metrics | `FACT_NETWORK_KPI` | Same name | `latency_ms`, `throughput_mbps`, `packet_loss_pct`, `call_drop_rate_pct`, `signal_strength_dbm`, `handover_success_pct`, `active_connections` |
| Constant | `FACT_NETWORK_KPI` | `reading_count` | Default 1 |

### 4. Dimension & Fact Loading Sequence
1. Populate `DIM_CUSTOMER` (7,043 rows) and build in-memory `customerID` $\rightarrow$ `customer_key` hash map.
2. Populate `DIM_PLAN` (2,386 distinct plan combinations) and build plan attributes tuple $\rightarrow$ `plan_key` hash map.
3. Populate `DIM_CELL` (120 rows), `DIM_REGION` (5 rows), `DIM_NETWORK_TECH` (2 rows), and `DIM_TIME` (30 rows).
4. Resolve surrogate foreign keys for fact tables with strict zero-tolerance validation (any unmapped foreign key raises an ETL exception).
5. Load `FACT_CUSTOMER_CHURN` (7,043 rows) and `FACT_NETWORK_KPI` (3,600 rows).

### 5. How to Run the ETL Pipeline
To execute the complete end-to-end pipeline from scratch:
```powershell
python scripts/run_etl.py --reset
```
The `--reset` flag:
1. Rebuilds the warehouse schema from `database/schema.sql`.
2. Runs `scripts/etl_customer.py`.
3. Runs `scripts/etl_network.py`.
4. Executes the automated post-load validation suite.

### 6. Validation Suite & Reconciled Metrics
The validation suite in `scripts/run_etl.py` checks:
- **`PRAGMA integrity_check`:** Verifies database file consistency (`PASS`).
- **`PRAGMA foreign_key_check`:** Verifies zero orphaned fact records (`0 violations`).
- **Row Reconciliation:**
  - Customer: 7,043 source $\rightarrow$ 7,043 staging $\rightarrow$ 7,043 dimension $\rightarrow$ 7,043 fact rows (`100% reconciliation`).
  - Network: 3,600 source $\rightarrow$ 3,600 staging $\rightarrow$ 3,600 fact rows (`100% reconciliation`).
- **Analytical Metrics Match:**
  - Churned Customers: exactly 1,869 (26.54%).
  - Non-churned Customers: exactly 5,174 (73.46%).
  - Average Monthly Charges: exactly $64.7617.
  - Sum of Total Charges: exactly $16,056,168.70.
  - Network KPI averages match source CSV to 6 decimal places (Latency: 20.7884 ms, Throughput: 287.2645 Mbps, Packet Loss: 1.0982%, Call Drop Rate: 0.7300%, Active Connections: 289.38).

