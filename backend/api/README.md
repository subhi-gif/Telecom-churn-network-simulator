# Telecom Churn & Network Analysis REST API Service Layer (Step 7)

## 1. Architecture
The **Backend REST API Service Layer** connects the SQLite Star Schema analytical data warehouse (`database/warehouse.db`), the Multidimensional OLAP Engine, the Machine Learning & Association Mining pipelines, and the In-Memory Telecom Network Simulation Engine to interactive frontend visualization dashboards.

```
                      +-----------------------------------+
                      |   Frontend Dashboard (React/Vite) |
                      +-----------------+-----------------+
                                        | HTTP / JSON
                                        v
                      +-----------------+-----------------+
                      |     FastAPI Service Layer         |
                      |       (backend/api/main.py)       |
                      +----+--------+--------+--------+---+
                           |        |        |        |
        +------------------+        |        |        +------------------+
        v                           v        v                           v
+---------------+     +-------------+   +----+--------+     +------------+------+
| Health, Cells |     |    OLAP     |   | Data Mining |     | In-Memory Network |
|   & Network   |     |   Engine    |   |  Artifacts  |     | Simulation Engine |
+-------+-------+     +------+------+   +----+--------+     +------------+------+
        |                    |               |                           |
        +--------+-----------+               v                           v
                 |               results/*.json, *.csv             RAM / Ephemeral
                 v
+----------------+------------------+
|   database/warehouse.db (SQLite)  |
|  (Read-Only Star Schema Facts)    |
+-----------------------------------+
```

### Module Structure
```
backend/api/
├── __init__.py           # Package exports (app)
├── main.py               # FastAPI application factory, CORS, and exception handlers
├── dependencies.py       # Database connection generator & SimulationEngine singleton
├── schemas.py            # Pydantic v2 validation models & standard response envelopes
├── routes/
│   ├── __init__.py       # Aggregated api_router
│   ├── health.py         # GET /api/health (database connectivity check)
│   ├── cells.py          # GET /api/cells, GET /api/cells/{cell_id}
│   ├── network.py        # GET /api/network/{cell_id}, GET /api/network/{cell_id}/summary
│   ├── olap.py           # Customer & Network OLAP routes (summary, rollup, drilldown, slice, dice)
│   ├── mining.py         # Churn prediction, clustering, association rules, summary
│   └── simulation.py     # State, cell selection, scenario control, time stepping, comparisons, events
└── README.md             # Complete API documentation & developer guide
```

---

## 2. Installation
Ensure Python 3.10+ (tested through Python 3.14) is available. Dependencies required:
- `fastapi >= 0.115.0`
- `uvicorn >= 0.30.0`
- `pydantic >= 2.0.0`
- `httpx >= 0.27.0` (for testing and client queries)
- `pandas`, `numpy`, `scikit-learn`

Install via pip if needed:
```bash
pip install fastapi uvicorn "pydantic>=2.0" httpx
```

---

## 3. Starting the Server

### Development Mode (with hot-reload):
```bash
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 --reload
```

### Production / Standalone Mode:
```bash
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Interactive Documentation UIs:
- **Swagger UI (Interactive API Docs):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc (Specification Viewer):** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **OpenAPI Schema (JSON):** [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

---

## 4. API Endpoints Catalog

### Health & System
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Verifies service health and warehouse connectivity. |
| `GET` | `/` | Returns service metadata and documentation links. |

### Cell Inventory
| Method | Endpoint | Parameters | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/cells` | `region`, `technology` | Lists available radio cells in `DIM_CELL`. |
| `GET` | `/api/cells/{cell_id}` | Path: `cell_id` | Returns metadata, technology, observation count, and time range. |

### Network KPI Telemetry
| Method | Endpoint | Parameters | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/network/{cell_id}` | `start_time`, `end_time`, `limit` | Returns actual time-series observations from `FACT_NETWORK_KPI`. |
| `GET` | `/api/network/{cell_id}/summary` | Path: `cell_id` | Returns aggregate statistics (avg, min, max) for cell telemetry. |

### Multidimensional OLAP Engine
| Method | Endpoint | Parameters | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/olap/customer/summary` | None | Total customers, churn rate, monthly & total charges. |
| `GET` | `/api/olap/customer/rollup` | `group_by` | Roll-up along contract, internet service, payment method, tenure. |
| `GET` | `/api/olap/customer/drilldown`| `tenure_band` | Drill down from tenure band into contract distribution. |
| `GET` | `/api/olap/customer/slice` | `dimension`, `value` | Slice customer star schema by a specific dimension value. |
| `GET` | `/api/olap/customer/dice` | `contract`, `internet_service`, etc. | Multi-dimensional dice filtering. |
| `GET` | `/api/olap/network/summary` | None | Total observations, cell counts, network-wide average KPIs. |
| `GET` | `/api/olap/network/rollup` | `level` (hour, region, technology) | Temporal or categorical network rollup. |
| `GET` | `/api/olap/network/drilldown`| `region`, `cell_id` | Regional drill down to individual cells. |
| `GET` | `/api/olap/network/slice` | `dimension`, `value` | Slice network telemetry by dimension value. |
| `GET` | `/api/olap/network/dice` | `region`, `technology`, timestamps | Multi-dimensional network dice filtering. |
| `GET` | `/api/olap/network/high-call-drop` | `threshold` (default 2.0%) | Analytical query returning cells exceeding threshold. |

### Data Mining & ML Models
| Method | Endpoint | Parameters | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/mining/summary` | None | Overview of churn models, clustering metrics, and association rules. |
| `GET` | `/api/mining/churn` | None | Logistic Regression & Decision Tree metrics, feature importances. |
| `GET` | `/api/mining/clusters` | None | K-Means inertia, silhouette evaluation across K=2..5, and cluster profiles. |
| `GET` | `/api/mining/association-rules` | `churn_only`, `min_confidence`, `limit` | Apriori customer service pattern rules with Support, Confidence, Lift. |

### Network Simulation Engine
| Method | Endpoint | Body | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/simulation/state` | None | Current simulated cell state, health score, and active alerts. |
| `POST` | `/api/simulation/select-cell`| `{"cell_id": "Cell_0025"}` | Loads authentic baseline observation from warehouse. |
| `POST` | `/api/simulation/scenario` | `{"scenario": "...", "severity": "..."}` | Applies scenario (NORMAL, CONGESTION, etc.) and severity. |
| `POST` | `/api/simulation/update` | `{"delta_time": 1.0}` | Advances simulation clock by `delta_time` seconds. |
| `POST` | `/api/simulation/pause` | None | Pauses simulation clock. |
| `POST` | `/api/simulation/resume` | None | Resumes simulation clock. |
| `POST` | `/api/simulation/reset` | None | Restores pristine warehouse baseline. |
| `GET` | `/api/simulation/comparison`| None | Returns baseline vs simulated delta comparisons for all 7 KPIs. |
| `GET` | `/api/simulation/events` | None | Returns in-memory simulation audit log. |
| `DELETE`| `/api/simulation/events` | None | Clears in-memory simulation audit log. |

---

## 5. Request & Response Examples

### Example 1: Cell Details (`GET /api/cells/Cell_0025`)
**Request:**
```http
GET /api/cells/Cell_0025 HTTP/1.1
Host: 127.0.0.1:8000
```
**Response (HTTP 200):**
```json
{
  "success": true,
  "data": {
    "cell_id": "Cell_0025",
    "region": "Central",
    "technology": "5G",
    "available_observation_count": 30,
    "time_range": {
      "start_time": "2026-08-03 14:00:00",
      "end_time": "2026-08-03 14:29:00"
    }
  }
}
```

### Example 2: Apply Simulation Scenario (`POST /api/simulation/scenario`)
**Request:**
```http
POST /api/simulation/scenario HTTP/1.1
Host: 127.0.0.1:8000
Content-Type: application/json

{
  "scenario": "CONGESTION",
  "severity": "HIGH"
}
```
**Response (HTTP 200):**
```json
{
  "success": true,
  "data": {
    "simulation": true,
    "simulation_active": true,
    "cell": {
      "cell_id": "Cell_0025",
      "region": "Central",
      "technology": "5G",
      "timestamp": "2026-08-03 14:00:00"
    },
    "scenario": "CONGESTION",
    "severity": "HIGH",
    "simulation_time": 0.0,
    "baseline": {
      "latency_ms": 3.73,
      "throughput_mbps": 289.16,
      "packet_loss_pct": 1.179,
      "call_drop_rate_pct": 0.607,
      "signal_strength_dbm": -63.7,
      "handover_success_pct": 97.21,
      "active_connections": 395
    },
    "current": {
      "latency_ms": 3.73,
      "throughput_mbps": 289.16,
      "packet_loss_pct": 1.179,
      "call_drop_rate_pct": 0.607,
      "signal_strength_dbm": -63.7,
      "handover_success_pct": 97.21,
      "active_connections": 395
    },
    "health_score": 89.2,
    "alerts": []
  }
}
```

---

## 6. Error Handling Structure
All API errors return consistent JSON payloads without exposing Python stack traces:

```json
{
  "success": false,
  "error": {
    "code": "CELL_NOT_FOUND",
    "message": "Cell 'Cell_9999' does not exist in the warehouse."
  }
}
```

### Standard Error Codes:
- `CELL_NOT_FOUND` (HTTP 404): Specified cell does not exist in `DIM_CELL`.
- `INVALID_SCENARIO` (HTTP 400): Unknown scenario name provided.
- `INVALID_SEVERITY` (HTTP 400): Severity outside `LOW`, `MEDIUM`, `HIGH`.
- `INVALID_DELTA_TIME` (HTTP 400): Time step $\le 0.0$ or $> 60.0$ seconds.
- `VALIDATION_ERROR` (HTTP 400): Pydantic input model validation error.
- `INTERNAL_SERVER_ERROR` (HTTP 500): Unexpected system exception (sanitized).

---

## 7. Database Safety & Immutability Rules
1. **Zero SQL Mutations:** The API layer never executes `INSERT`, `UPDATE`, `DELETE`, `DROP`, or `ALTER` statements on `warehouse.db`.
2. **Parameterized Queries:** All SQL queries use SQLite parameter bindings (`?`) to eliminate SQL injection risks.
3. **Decoupled Simulation:** Simulation state transitions, health scores, and event logs exist **strictly in-memory** and never alter `FACT_NETWORK_KPI`.
4. **Preserved Integrity:** Verified across all automated test suites:
   - `FACT_NETWORK_KPI`: Exactly 3,600 rows.
   - `FACT_CUSTOMER_CHURN`: Exactly 7,043 rows.
   - `PRAGMA integrity_check`: Returns `"ok"`.

---

## 8. Simulation API Workflow
A typical frontend simulation session proceeds through the following sequential calls:
1. `POST /api/simulation/select-cell` with `{"cell_id": "Cell_0025"}` to establish the ground-truth baseline.
2. `POST /api/simulation/scenario` with `{"scenario": "CONGESTION", "severity": "HIGH"}`.
3. Repeated `POST /api/simulation/update` with `{"delta_time": 1.0}` on each animation frame or timer tick to advance telemetry.
4. `GET /api/simulation/comparison` to populate the baseline-vs-simulated comparison delta widget.
5. `POST /api/simulation/reset` to restore nominal baseline conditions.

---

## 9. Frontend Integration Notes
- **CORS Configuration:** By default, origins `http://localhost:3000`, `http://localhost:5173`, `http://127.0.0.1:3000`, and `http://127.0.0.1:5173` are permitted. To customize, set the environment variable `CORS_ORIGINS`:
  ```bash
  export CORS_ORIGINS="http://localhost:5173,https://my-dashboard.local"
  ```
- **Consistent Response Wrapping:** Frontend clients can expect top-level `success: true` and payload under `data`, or `success: false` and error under `error`.
- **Pagination & Bounds:** Time-series network queries enforce a default limit of 100 observations (maximum 1,000) to prevent oversized payloads over network sockets.

---

## 10. Automated Validation
Run the full 24-check API validation suite:
```bash
python scripts/test_api.py
```
Expected output: `24/24 checks passed.`
