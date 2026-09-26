# Telecom Network Simulation Engine (Step 6)

## 1. Purpose of the Simulation Engine
The **Telecom Network Simulation Engine** provides a stateful, deterministic, in-memory discrete-event simulation layer for cellular Radio Access Network (RAN) telemetry. It bridges authentic historical operational baselines stored in the analytical data warehouse (`database/warehouse.db`) with dynamic real-time degradation scenarios.

This layer enables:
- Interactive what-if degradation testing (e.g. flash crowd congestion, RF attenuation, cell sector overload).
- Deterministic synthetic telemetry generation strictly bounded by cellular domain physical limits.
- Real-time KPI delta comparison against ground-truth warehouse baselines.
- Real-time composite health scoring (0–100) and alert detection.
- A decoupled, strictly in-memory foundation for future API endpoints and frontend dashboards without ever altering historical warehouse facts.

---

## 2. Baseline Data Source
The simulation engine does **not** generate synthetic cells or fake historical baselines. All simulations are grounded in actual observations from the star schema warehouse:

- **Warehouse Path:** `database/warehouse.db`
- **Fact Table:** `FACT_NETWORK_KPI` (3,600 total observations across 120 cells and 30 timestamps)
- **Dimension Tables:**
  - `DIM_CELL`: Sector identity (`cell_id`), latitude, longitude, cell type.
  - `DIM_REGION`: Administrative geographic regions (`region_name`).
  - `DIM_NETWORK_TECH`: Radio generation (`technology_name`: `3G`, `4G`, `5G`).
  - `DIM_TIME`: Temporal hierarchy (`timestamp`, hour, day, month, year).

### Default Demonstration Cell: `Cell_0025`
By default, the engine loads `Cell_0025`, an authentic high-throughput 5G cell located in the `Central` region:
- **Cell ID:** `Cell_0025`
- **Region:** `Central`
- **Technology:** `5G`
- **Initial Observation Timestamp:** `2026-08-03 14:00:00`
- **Baseline Telemetry:**
  - Latency: `3.73 ms`
  - Throughput: `289.16 Mbps`
  - Packet Loss: `1.179 %`
  - Call Drop Rate: `0.607 %`
  - Signal Strength: `-63.70 dBm`
  - Handover Success: `97.21 %`
  - Active Connections: `395`

---

## 3. Architecture and Module Structure
The simulation package is organized modularly under `backend/simulation/`:

```
backend/simulation/
├── __init__.py           # Package exports for clean public API
├── engine.py             # Stateful SimulationEngine orchestrator & event loop
├── network_state.py      # NetworkState dataclass & comparison utilities
├── scenarios.py          # Scenario profiles, multipliers, deltas & clamping
├── metrics.py            # Health Score formula & threshold alert detectors
└── README.md             # Architecture & operational documentation
```

### Module Responsibilities:
1. **`network_state.py`**: Encapsulates cell coordinates, topological metadata, an immutable reference dictionary of baseline KPIs, dynamic simulated values, active alerts, and serializable delta comparison tables.
2. **`scenarios.py`**: Houses mathematical definitions of operational degradation matrices across scenarios and severities, as well as domain-safe boundary clamping functions.
3. **`metrics.py`**: Evaluates the transparent composite 0–100 Simulation Health Score and scans telemetry against configurable operational alert thresholds.
4. **`engine.py`**: Manages the simulation life cycle (loading baselines from SQLite, advancing discrete time steps, smoothing state transitions, pause/resume, reset, and event logging).

---

## 4. Network State Representation (`NetworkState`)
The `NetworkState` dataclass manages live telemetry and preserves ground-truth baseline values:

```python
@dataclass
class NetworkState:
    region: str
    cell_id: str
    technology: str
    timestamp: str

    latency_ms: float
    throughput_mbps: float
    packet_loss_pct: float
    call_drop_rate_pct: float
    signal_strength_dbm: float
    handover_success_pct: float
    active_connections: int

    scenario_name: str = "NORMAL"
    severity: str = "LOW"
    simulation_time: float = 0.0
    health_score: float = 100.0
    alerts: List[Dict[str, Any]] = field(default_factory=list)
    baseline_values: Dict[str, Any] = field(default_factory=dict)
```

### State Methods:
- `simulated_values`: Returns rounded dictionary of current simulated KPIs.
- `reset_to_baseline()`: Restores live KPIs from `baseline_values`, sets scenario to `"NORMAL"`, clears alerts, and resets clock.
- `get_comparison()`: Returns a list of comparison dicts detailing metric key, display name, baseline, simulated, absolute difference, and percentage difference.
- `to_dict()`: Serializes complete state to JSON-ready dictionary.

---

## 5. Degradation Scenarios
The engine provides 5 distinct operational scenarios:

| Scenario | Operational Domain Rationale | Primary Affected Telemetry |
| :--- | :--- | :--- |
| `NORMAL` | Pristine nominal operations. Identical to warehouse baseline. | All KPIs maintain baseline values. |
| `CONGESTION` | High traffic density and queue bufferbloat. | `active_connections` ↑, `latency_ms` ↑, `throughput_mbps` ↓, `packet_loss_pct` ↑, `call_drop_rate_pct` ↑. |
| `SIGNAL_DEGRADATION` | RF attenuation, multipath fading, or antenna misalignment. | `signal_strength_dbm` ↓, `packet_loss_pct` ↑, `call_drop_rate_pct` ↑, `handover_success_pct` ↓. |
| `CELL_OVERLOAD` | Extreme capacity saturation exceeding sector scheduler capacity. | Severe connection spike (up to 6x), throughput collapse (-90%), extreme call drops (>10%). |
| `RECOVERY` | Gradual return toward warehouse baseline steady-state. | Telemetry smoothly converges back to initial baseline at rate $\alpha = 0.25 \times \Delta t$. |

---

## 6. Severity Levels & Parameter Multipliers
Each degradation scenario supports three severity tiers (`LOW`, `MEDIUM`, `HIGH`):

### 1. `CONGESTION` Matrix
- **`LOW`**: Active connections +30%, Latency +25%, Throughput -15%, Packet loss +0.5%, Call drop +0.3%, Handover $\times 0.985$.
- **`MEDIUM`**: Active connections +75%, Latency +65%, Throughput -35%, Packet loss +1.8%, Call drop +0.95%, Handover $\times 0.96$.
- **`HIGH`**: Active connections +150%, Latency +140%, Throughput -60%, Packet loss +4.5%, Call drop +2.4%, Handover $\times 0.91$.

### 2. `SIGNAL_DEGRADATION` Matrix
- **`LOW`**: Signal strength -10 dBm, Packet loss +1.5%, Call drop +0.6%, Latency +20%, Throughput -15%, Handover $\times 0.96$.
- **`MEDIUM`**: Signal strength -22 dBm, Packet loss +3.5%, Call drop +1.5%, Latency +60%, Throughput -35%, Handover $\times 0.92$.
- **`HIGH`**: Signal strength -38 dBm, Packet loss +8.0%, Call drop +4.2%, Latency +150%, Throughput -65%, Handover $\times 0.82$.

### 3. `CELL_OVERLOAD` Matrix
- **`LOW`**: Active connections +100%, Latency +80%, Throughput -45%, Packet loss +2.5%, Call drop +1.2%, Handover $\times 0.94$.
- **`MEDIUM`**: Active connections +250%, Latency +250%, Throughput -70%, Packet loss +6.5%, Call drop +3.2%, Handover $\times 0.85$.
- **`HIGH`**: Active connections +500%, Latency +700%, Throughput -90%, Packet loss +16.0%, Call drop +10.5%, Handover $\times 0.75$.

---

## 7. KPI Transformation Formulas and Clipping Bounds
Target steady-state values are calculated via:
$$\text{Target} = \text{clamp}\Big((\text{Baseline} \times \text{Multiplier}) + \text{Additive Delta}\Big)$$

Discrete time-step transitions evolve smoothly using exponential moving convergence:
$$\text{KPI}_{t+\Delta t} = \text{KPI}_t + \text{rate} \times (\text{Target} - \text{KPI}_t)$$
where $\text{rate} = \min(1.0, 0.35 \times \Delta t)$ for degradation and $\min(1.0, 0.25 \times \Delta t)$ for recovery.

### Physical Boundary Clamping
Simulated telemetry cannot violate physical RF limits:

| Metric | Lower Bound | Upper Bound | Domain Rationale |
| :--- | :---: | :---: | :--- |
| `latency_ms` | `1.0 ms` | `1000.0 ms` | Propagation delay floor to TCP timeout ceiling |
| `throughput_mbps` | `0.0 Mbps` | `1200.0 Mbps` | Practical 5G downlink cell capacity limit |
| `packet_loss_pct` | `0.0 %` | `100.0 %` | Physical percentage boundaries |
| `call_drop_rate_pct` | `0.0 %` | `100.0 %` | Physical percentage boundaries |
| `signal_strength_dbm` | `-120.0 dBm` | `-35.0 dBm` | RF receiver noise floor to amplifier saturation |
| `handover_success_pct` | `0.0 %` | `100.0 %` | Physical percentage boundaries |
| `active_connections` | `0` | `5000` | Hardware scheduler sector limit |

---

## 8. Simulation Health Score Formula
The **Simulation Health Score** is a transparent composite index bounded strictly in $[0.0, 100.0]$:

$$\text{Health Score} = 100 - (P_{\text{drop}} + P_{\text{loss}} + P_{\text{latency}} + P_{\text{signal}} + P_{\text{handover}})$$

### Component Penalty Deductions:
1. **Call Drop Penalty ($P_{\text{drop}}$, max 30 pts):**
   $$P_{\text{drop}} = \min(30.0, \max(0.0, \text{call\_drop\_rate\_pct} \times 10.0))$$
   *(A 3.0% call drop rate exhausts all 30 points).*
2. **Packet Loss Penalty ($P_{\text{loss}}$, max 20 pts):**
   $$P_{\text{loss}} = \min(20.0, \max(0.0, \text{packet\_loss\_pct} \times 4.0))$$
   *(A 5.0% packet loss exhausts all 20 points).*
3. **Latency Penalty ($P_{\text{latency}}$, max 20 pts):**
   $$P_{\text{latency}} = \min(20.0, \max(0.0, (\text{latency\_ms} - 20.0) \times 0.25))$$
   *(Latencies $\le 20\text{ ms}$ incur 0 penalty; $100\text{ ms}$ incurs the full 20-point penalty).*
4. **Signal Attenuation Penalty ($P_{\text{signal}}$, max 15 pts):**
   $$P_{\text{signal}} = \min(15.0, \max(0.0, (-70.0 - \text{signal\_strength\_dbm}) \times 0.5))$$
   *(Signal $\ge -70\text{ dBm}$ incurs 0 penalty; $-100\text{ dBm}$ incurs the full 15-point penalty).*
5. **Handover Failure Penalty ($P_{\text{handover}}$, max 15 pts):**
   $$P_{\text{handover}} = \min(15.0, \max(0.0, (96.0 - \text{handover\_success\_pct}) \times 1.5))$$
   *(Handover $\ge 96\%$ incurs 0 penalty; $\le 86\%$ incurs the full 15-point penalty).*

---

## 9. Degradation Alerts and Threshold Rules
All generated alerts are tagged with `[SIMULATED CONDITION]` and contain explicit threshold justifications:

| Alert Code | Severity | Analytical Trigger Condition | Description |
| :--- | :---: | :--- | :--- |
| `HIGH_CALL_DROP` | `CRITICAL` (>5%) / `WARNING` (>2%) | `call_drop_rate_pct > 2.0%` | Simulated call drop rate exceeds analytical churn threshold. |
| `HIGH_PACKET_LOSS` | `CRITICAL` (>10%) / `WARNING` (>3%) | `packet_loss_pct > 3.0%` | Simulated IP packet loss exceeds streaming/voice tolerance. |
| `HIGH_LATENCY` | `CRITICAL` (>200ms) / `WARNING` (>80ms) | `latency_ms > 80.0 ms` | Simulated round-trip latency exceeds QoS interactive threshold. |
| `LOW_HANDOVER_SUCCESS` | `CRITICAL` (<80%) / `WARNING` (<90%) | `handover_success_pct < 90.0%` | Simulated inter-cell mobility handovers failing below acceptable floor. |

---

## 10. Baseline vs Simulated Comparison
The `engine.get_comparison()` method produces structured delta rows:

$$\text{Absolute Delta} = \text{Simulated} - \text{Baseline}$$
$$\text{Percentage Delta} = \frac{\text{Absolute Delta}}{|\text{Baseline}|} \times 100$$

### Sample Output from Demonstration:
```
Metric                    | Baseline   | Simulated  | Abs Diff   | % Diff    
--------------------------|------------|------------|------------|-----------
Latency (ms)              | 3.73       | 8.91       | 5.18       | +138.87 %
Throughput (Mbps)         | 289.16     | 116.65     | -172.51    | -59.66  %
Packet Loss (%)           | 1.179      | 5.643      | 4.464      | +378.63 %
Call Drop Rate (%)        | 0.607      | 2.987      | 2.38       | +392.09 %
Signal Strength (dBm)     | -63.7      | -66.68     | -2.98      | -4.68   %
Handover Success (%)      | 97.21      | 88.53      | -8.68      | -8.93   %
Active Connections        | 395        | 983        | 588        | +148.86 %
```

---

## 11. Event Logging System
The simulation engine logs all state transitions to an in-memory chronological audit log:
- `BASELINE_LOADED`: Initial cell baseline queried from warehouse.
- `SCENARIO_APPLIED`: Scenario or severity change applied by operator.
- `ALERT_TRIGGERED`: Telemetry crossed degradation threshold.
- `SIMULATION_PAUSED`: Clock paused.
- `SIMULATION_RESUMED`: Clock resumed.
- `SIMULATION_RESET`: Pristine warehouse state restored.

Every event records: `simulation_time`, `event_type`, `cell_id`, `region`, `technology`, `scenario`, `severity`, and descriptive `message`.

---

## 12. Warehouse Immutability Rules
The simulation engine adheres to strict database integrity constraints:
1. **Zero SQL DDL/DML Mutations:** No `INSERT`, `UPDATE`, `DELETE`, `DROP`, or `ALTER` statements are ever executed against `warehouse.db`.
2. **Read-Only SQLite Access:** Initial baselines are queried via standard `SELECT` queries.
3. **Decoupled Memory Allocation:** All simulated telemetry is maintained in standard Python dataclasses and dictionaries.
4. **Pre- & Post-Simulation Verification:** Verified by automated tests:
   - `FACT_NETWORK_KPI`: Exactly 3,600 rows.
   - `FACT_CUSTOMER_CHURN`: Exactly 7,043 rows.
   - `PRAGMA integrity_check`: Returns `"ok"`.

---

## 13. How to Run Tests and Demonstration

### Run Comprehensive 18-Check Validation Suite:
```bash
python scripts/test_simulation.py
```

### Quick Python Code Example:
```python
from backend.simulation import SimulationEngine

# Initialize engine with authentic warehouse cell
engine = SimulationEngine(default_cell_id="Cell_0025")

# Check baseline state
print("Baseline Cell:", engine.state.cell_id, engine.state.technology)
print("Initial Health Score:", engine.state.health_score)

# Apply high congestion
engine.apply_scenario("CONGESTION", "HIGH")

# Advance simulation by 5 seconds
engine.step(5.0)

# Inspect comparisons and active alerts
for comp in engine.get_comparison():
    print(f"{comp['metric_name']}: {comp['baseline']} -> {comp['simulated']} ({comp['percentage_difference']}%)")

for alert in engine.state.alerts:
    print(f"Alert: {alert['alert_type']} - {alert['message']}")

# Restore pristine baseline
engine.reset()
```

---

## 14. Limitations and Boundaries
- **In-Memory Only:** The engine does not persist simulated runs into `warehouse.db`. Simulated states are ephemeral.
- **Single Sector Focus:** The engine models isolated cell behavior; it does not model cross-cell radio interference or neighbor propagation.
- **Analytical Approximation:** The continuous state update uses deterministic smoothing rather than discrete-event RF ray-tracing or physical packet transmission queues.
- **No Customer-to-Cell Bridge:** In accordance with architectural project rules, simulated degradation in a cell does not automatically churn individual customer records in `FACT_CUSTOMER_CHURN`.
