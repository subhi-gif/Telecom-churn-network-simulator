# Telecom OLAP Analytical Engine

Online Analytical Processing (OLAP) multidimensional analysis layer for the Telecom Customer Churn and Network Performance Data Warehouse (`database/warehouse.db`).

---

## 1. What OLAP Means in This Project

In this project, **OLAP (Online Analytical Processing)** provides a structured, high-performance, and multidimensional query engine designed specifically for analytical exploration rather than transactional updates (OLTP).

### Decoupled Data Marts Rule
The analytical warehouse contains **two strictly isolated star schemas**:
1. **Customer Churn Mart**: Centered around customer subscription snapshots and churn behaviors (`FACT_CUSTOMER_CHURN`).
2. **Network Performance Mart**: Centered around minute-by-minute cell site telemetry (`FACT_NETWORK_KPI`).

> [!IMPORTANT]
> **No Customer-to-Cell Bridge**: There is **no legitimate foreign key relationship** between individual customer churn records and physical cell sites in the underlying data. The OLAP engine strictly enforces this architectural boundary: **it never executes cross-fact joins between customer and network data, nor does it attribute individual churn events to specific cell towers**. Any cross-domain correlation must occur exclusively through valid macro-level statistical summaries.

---

## 2. Customer Cube

The Customer Cube organizes customer accounts and subscriptions across several analytical dimensions:

### Dimensions
- **Tenure Band**: Derived customer lifecycle duration (`0-12 months`, `13-24 months`, `25-48 months`, `49-72 months`).
- **Contract**: Billing commitment (`Month-to-month`, `One year`, `Two year`).
- **Internet Service**: Network connection type (`DSL`, `Fiber optic`, `No`).
- **Payment Method**: Billing conduit (`Electronic check`, `Mailed check`, `Bank transfer (automatic)`, `Credit card (automatic)`).
- **Demographics & Add-on Services**: `gender`, `SeniorCitizen`, `Partner`, `Dependents`, `OnlineSecurity`, `TechSupport`, etc.

### Core Metrics (Measures)
- `customer_count`: Total active accounts in segment.
- `churned_customers`: Number of accounts that cancelled service (`churn_flag = 1`).
- `non_churned_customers`: Retained accounts (`churn_flag = 0`).
- `churn_rate_pct`: Churn percentage (`(churned / count) * 100`).
- `avg_monthly_charges`: Average recurring monthly bill ($).
- `avg_total_charges`: Cumulative lifetime spend ($).

---

## 3. Network Cube

The Network Cube models radio access telemetry across spatial, topological, and temporal dimensions:

### Dimensions
- **Region**: Macro-geographic market (`Central`, `East`, `North`, `South`, `West`).
- **Cell Site**: Physical transmitter node (`Cell_0001` through `Cell_0120`).
- **Technology**: Radio access technology (`LTE`, `5G`).
- **Time**: Discrete 1-minute telemetry observation intervals (`timestamp`, `date`, `hour`, `minute`, `day`, `month`, `year`).

### Core Metrics (Measures)
- `avg_latency_ms`: Round-trip packet latency in milliseconds.
- `avg_throughput_mbps`: Downlink data transfer rate in megabits per second.
- `avg_packet_loss_pct`: Percentage of dropped IP packets.
- `avg_call_drop_rate_pct`: Percentage of voice/VoLTE calls abnormally terminated.
- `avg_signal_strength_dbm`: Received Signal Strength Indicator (RSSI) in dBm.
- `avg_handover_success_pct`: Percentage of seamless inter-cell transitions.
- `avg_active_connections`: Concurrent attached user equipment count.

---

## 4. Roll-Up

Roll-up aggregates data from detailed records up to broader analytical groupings.

### Customer Roll-Up (`Customer -> Tenure Band`)
Aggregates 7,043 individual customer rows into 4 lifecycle stages:

```python
from backend.olap import get_customer_rollup

rollup = get_customer_rollup(group_by="tenure_band")
```

**Actual Database Results**:
| Tenure Band | Customer Count | Churned Customers | Non-Churned Customers | Churn Rate (%) | Avg Monthly ($) | Avg Total ($) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **0-12 months** | 2,186 | 1,037 | 1,149 | 47.44% | $56.10 | $275.23 |
| **13-24 months** | 1,024 | 294 | 730 | 28.71% | $61.36 | $1,126.26 |
| **25-48 months** | 1,594 | 325 | 1,269 | 20.39% | $65.93 | $2,390.45 |
| **49-72 months** | 2,239 | 213 | 2,026 | 9.51% | $73.95 | $4,685.51 |
| **Total / Reconciled** | **7,043** | **1,869** | **5,174** | **26.54%** | **$64.76** | **$2,279.73** |

### Network Roll-Up (`Minute -> Hour -> Day -> Month`)
Aggregates telemetry from individual 1-minute intervals up to hourly, daily, and monthly buckets:

```python
from backend.olap import get_network_rollup

# Level options: 'minute', 'hour', 'day', 'month'
min_rollup = get_network_rollup(level="minute")  # Returns 30 rows (one per minute)
hour_rollup = get_network_rollup(level="hour")    # Returns 1 row (14:00:00)
day_rollup = get_network_rollup(level="day")      # Returns 1 row (2026-08-03)
month_rollup = get_network_rollup(level="month")  # Returns 1 row (2026-08)
```

---

## 5. Drill-Down

Drill-down navigates from an aggregated summary down into more granular component dimensions.

### Customer Drill-Down (`Tenure Band -> Contract`)
Drills down into the specific contract mix for a chosen tenure cohort:

```python
from backend.olap import get_customer_drilldown

drilldown = get_customer_drilldown(tenure_band="0-12 months")
```

**Actual Database Results for "0-12 months"**:
| Contract Type | Customer Count | Churned Customers | Churn Rate (%) | Avg Monthly Charges ($) |
| :--- | :---: | :---: | :---: | :---: |
| **Month-to-month** | 1,994 | 1,024 | 51.35% | $58.22 |
| **One year** | 124 | 13 | 10.48% | $35.80 |
| **Two year** | 68 | 0 | 0.00% | $30.95 |
| **Sum** | **2,186** | **1,037** | **47.44%** | — |

### Network Drill-Down (`Region -> Cell -> Time`)
Drills down from a geographic region to its constituent cell towers, and further to time-series telemetry for a specific cell:

```python
from backend.olap import get_network_drilldown

# Level 1: Region -> Cell breakdown (returns 29 cell sites in North region)
north_cells = get_network_drilldown(region="North")

# Level 2: Region -> Cell -> Time breakdown (returns 30 minute observations for Cell_0001)
cell_timeseries = get_network_drilldown(region="North", cell_id="Cell_0001")
```

---

## 6. Slice

Slicing extracts a subcube by fixing **exactly one dimension** to a specific value.

### Customer Slice Examples
```python
from backend.olap import get_customer_slice

# Slice 1: Month-to-month contract
slice_m2m = get_customer_slice(dimension="contract", value="Month-to-month")
# Result: 3,875 customers, 1,655 churned (42.71% churn rate), avg monthly: $66.40

# Slice 2: Fiber optic internet service
slice_fiber = get_customer_slice(dimension="internet_service", value="Fiber optic")
# Result: 3,096 customers, 1,297 churned (41.89% churn rate), avg monthly: $91.50
```

### Network Slice Examples
```python
from backend.olap import get_network_slice

# Slice 1: 5G technology
slice_5g = get_network_slice(dimension="technology", value="5G")
# Result: 1,710 observations, avg latency: 9.07 ms, avg throughput: 540.13 Mbps

# Slice 2: North region
slice_north = get_network_slice(dimension="region", value="North")
# Result: 870 observations, avg latency: 20.76 ms, avg throughput: 288.75 Mbps
```

---

## 7. Dice

Dicing extracts a subcube by applying **multiple simultaneous dimension filters and metric thresholds**.

### Customer Dice
```python
from backend.olap import get_customer_dice

high_risk_segment = get_customer_dice(
    contract="Month-to-month",
    internet_service="Fiber optic",
    tenure_band="0-12 months"
)
```
**Actual Database Result**:
- `customer_count`: 916
- `churned_count`: 643
- `non_churned_count`: 273
- `churn_rate_pct`: **70.20%**
- `avg_monthly_charges`: $82.08
- `avg_total_charges`: $402.19

### Network Dice
```python
from backend.olap import get_network_dice

degraded_5g = get_network_dice(
    region="North",
    technology="5G",
    call_drop_rate_gt=2.0
)
```
**Actual Database Result**:
- `observation_count`: 3
- `avg_latency_ms`: 220.46 ms
- `avg_throughput_mbps`: 416.63 Mbps
- `avg_packet_loss_pct`: 13.66%
- `avg_call_drop_rate_pct`: **11.01%**
- `avg_signal_strength_dbm`: -86.17 dBm

---

## 8. High-Call-Drop Analysis

Identifies cell sites experiencing severe call drop degradation above a configurable analytical threshold (default: `2.0%`).

```python
from backend.olap import get_high_call_drop_cells

# Configurable analytical threshold
high_drop = get_high_call_drop_cells(threshold=2.0)
```

**Analytical Findings**:
- Exactly **83 observations** across the 3,600 readings exceed the 2.0% threshold.
- Anomalies are grouped by `(region, cell_id, technology)`.
- Identifies critical hotspots (e.g. `Cell_0025` in `Central` experiencing up to 19.61% call drop rate with 203 ms latency).

---

## 9. Executive Summaries

### Customer Summary
```python
from backend.olap import get_customer_summary

summary = get_customer_summary()
```
```json
{
  "operation": "customer_summary",
  "status": "success",
  "results": {
    "total_customers": 7043,
    "churned_customers": 1869,
    "non_churned_customers": 5174,
    "churn_rate_pct": 26.54,
    "avg_monthly_charges": 64.76,
    "avg_total_charges": 2279.73
  }
}
```

### Network Summary
```python
from backend.olap import get_network_summary

summary = get_network_summary()
```
```json
{
  "operation": "network_summary",
  "status": "success",
  "results": {
    "total_observations": 3600,
    "number_of_cells": 120,
    "number_of_regions": 5,
    "number_of_technologies": 2,
    "avg_latency_ms": 20.79,
    "avg_throughput_mbps": 287.26,
    "avg_packet_loss_pct": 1.1,
    "avg_call_drop_rate_pct": 0.73,
    "avg_signal_strength_dbm": -58.43,
    "avg_handover_success_pct": 97.18,
    "avg_active_connections": 289.38
  }
}
```

---

## 10. How to Run the OLAP Tests

To execute the test suite and verify all operations, parameter bounds, mathematical reconciliations, and data model isolation:

```powershell
python scripts/test_olap.py
```

### Verification Checks Performed
1. **Customer Summary**: Matches 7,043 customers and 1,869 churned records.
2. **Customer Roll-Up**: Verifies tenure band count and churn totals reconcile to 7,043 and 1,869.
3. **Customer Drill-Down**: Verifies contract sub-segments sum precisely to parent band.
4. **Customer Slice**: Reconciles single-dimension slices against direct SQL.
5. **Customer Dice**: Validates multi-filter queries using parameterized SQL.
6. **Network Summary**: Matches 3,600 observations, 120 cells, 5 regions, 2 technologies.
7. **Network Roll-Up**: Validates 30 minutes, 1 hour, 1 day, 1 month time levels summing to 3,600 observations.
8. **Network Drill-Down**: Validates 29 North cells and 30-minute time-series per cell.
9. **Network Slice**: Validates 5G (1,710 obs) and North (870 obs) slices.
10. **Network Dice**: Validates multi-parameter condition queries.
11. **High-Call-Drop Analysis**: Validates extraction of all 83 high-drop observations.
12. **Negative / Controlled Error Handling**: Verifies graceful error dicts for invalid inputs without crashes.
13. **Data Model Isolation**: Confirms zero customer-to-cell tables/bridges and zero row mutations.
