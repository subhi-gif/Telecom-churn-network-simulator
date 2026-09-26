"""
Telecom Network Simulation Engine Module
Orchestrates discrete time-step simulation over real cell baselines from warehouse.db.
Supports pause, resume, reset, gradual transitions, alerting, event logging, and scenario comparisons.
"""

import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Union

from backend.olap.queries import get_connection
from backend.simulation.metrics import (
    DEFAULT_ALERT_THRESHOLDS,
    calculate_health_score,
    detect_degradation_alerts,
)
from backend.simulation.network_state import NetworkState
from backend.simulation.scenarios import (
    VALID_SCENARIOS,
    VALID_SEVERITIES,
    calculate_scenario_target,
    clamp_kpi_bounds,
)


class SimulationEngine:
    """
    Stateful in-memory discrete-event simulation engine for telecom radio cells.
    Operates without altering the analytical warehouse or source files.
    """

    def __init__(
        self,
        conn_or_path: Union[sqlite3.Connection, str, None] = None,
        default_cell_id: str = "Cell_0025",
        alert_thresholds: Optional[Dict[str, float]] = None,
    ):
        self.conn_or_path = conn_or_path
        self.default_cell_id = default_cell_id
        self.alert_thresholds = dict(alert_thresholds or DEFAULT_ALERT_THRESHOLDS)

        self.state: Optional[NetworkState] = None
        self._is_paused: bool = False
        self.event_log: List[Dict[str, Any]] = []

        # Automatically load initial demonstration baseline
        self.load_cell_baseline(default_cell_id)

    # -------------------------------------------------------------------------
    # 1. BASELINE LOADING FROM WAREHOUSE
    # -------------------------------------------------------------------------
    def load_cell_baseline(
        self,
        cell_id: str = "Cell_0025",
        timestamp: Optional[str] = None,
    ) -> NetworkState:
        """
        Loads an authentic observation from warehouse.db for a real cell.
        Initializes the NetworkState object without mutating the database.
        """
        clean_cell = str(cell_id).strip()

        if isinstance(self.conn_or_path, sqlite3.Connection):
            conn = self.conn_or_path
            owns_conn = False
        else:
            conn = get_connection(self.conn_or_path)
            owns_conn = True

        try:
            cur = conn.cursor()

            # Verify cell exists in DIM_CELL
            cur.execute("SELECT cell_key, cell_id FROM DIM_CELL WHERE cell_id = ?;", (clean_cell,))
            cell_row = cur.fetchone()
            if not cell_row:
                cur.execute("SELECT cell_id FROM DIM_CELL LIMIT 5;")
                samples = [r[0] for r in cur.fetchall()]
                raise ValueError(
                    f"Cell '{cell_id}' not found in DIM_CELL warehouse dimension. "
                    f"Valid sample cells: {samples}"
                )

            # Query baseline KPI observation
            if timestamp:
                sql = """
                    SELECT 
                        c.cell_id, r.region_name, tech.technology_name, t.timestamp,
                        f.latency_ms, f.throughput_mbps, f.packet_loss_pct,
                        f.call_drop_rate_pct, f.signal_strength_dbm,
                        f.handover_success_pct, f.active_connections
                    FROM FACT_NETWORK_KPI f
                    JOIN DIM_CELL c ON f.cell_key = c.cell_key
                    JOIN DIM_REGION r ON f.region_key = r.region_key
                    JOIN DIM_NETWORK_TECH tech ON f.technology_key = tech.technology_key
                    JOIN DIM_TIME t ON f.time_key = t.time_key
                    WHERE c.cell_id = ? AND t.timestamp = ?;
                """
                cur.execute(sql, (clean_cell, timestamp))
            else:
                sql = """
                    SELECT 
                        c.cell_id, r.region_name, tech.technology_name, t.timestamp,
                        f.latency_ms, f.throughput_mbps, f.packet_loss_pct,
                        f.call_drop_rate_pct, f.signal_strength_dbm,
                        f.handover_success_pct, f.active_connections
                    FROM FACT_NETWORK_KPI f
                    JOIN DIM_CELL c ON f.cell_key = c.cell_key
                    JOIN DIM_REGION r ON f.region_key = r.region_key
                    JOIN DIM_NETWORK_TECH tech ON f.technology_key = tech.technology_key
                    JOIN DIM_TIME t ON f.time_key = t.time_key
                    WHERE c.cell_id = ?
                    ORDER BY t.timestamp ASC
                    LIMIT 1;
                """
                cur.execute(sql, (clean_cell,))

            row = cur.fetchone()
            if not row:
                raise ValueError(f"No telemetry observations found in FACT_NETWORK_KPI for cell '{clean_cell}'.")

        finally:
            if owns_conn:
                conn.close()

        # Initialize NetworkState
        self.state = NetworkState(
            cell_id=row["cell_id"],
            region=row["region_name"],
            technology=row["technology_name"],
            timestamp=row["timestamp"],
            latency_ms=float(row["latency_ms"]),
            throughput_mbps=float(row["throughput_mbps"]),
            packet_loss_pct=float(row["packet_loss_pct"]),
            call_drop_rate_pct=float(row["call_drop_rate_pct"]),
            signal_strength_dbm=float(row["signal_strength_dbm"]),
            handover_success_pct=float(row["handover_success_pct"]),
            active_connections=int(row["active_connections"]),
        )

        # Compute initial baseline health score
        self.state.health_score = calculate_health_score(self.state.simulated_values)
        self.state.alerts = detect_degradation_alerts(
            self.state.simulated_values,
            self.state.simulation_time,
            self.alert_thresholds,
        )

        self._log_event(
            event_type="BASELINE_LOADED",
            message=f"Loaded warehouse baseline observation for {self.state.cell_id} ({self.state.region}, {self.state.technology}).",
        )

        return self.state

    # -------------------------------------------------------------------------
    # 2. SCENARIO CONFIGURATION & CONTROL
    # -------------------------------------------------------------------------
    def apply_scenario(self, scenario_name: str, severity: str = "MEDIUM") -> NetworkState:
        """Configures the active simulation scenario and severity level."""
        scen = scenario_name.strip().upper()
        sev = severity.strip().upper()

        if scen not in VALID_SCENARIOS:
            raise ValueError(f"Invalid scenario '{scenario_name}'. Valid: {sorted(list(VALID_SCENARIOS))}")
        if sev not in VALID_SEVERITIES:
            raise ValueError(f"Invalid severity '{severity}'. Valid: {sorted(list(VALID_SEVERITIES))}")

        self.state.scenario_name = scen
        self.state.severity = sev

        self._log_event(
            event_type="SCENARIO_APPLIED",
            message=f"Applied scenario '{scen}' with severity '{sev}' to {self.state.cell_id}.",
        )

        return self.state

    def pause(self):
        """Pauses time-stepping."""
        self._is_paused = True
        self._log_event("SIMULATION_PAUSED", "Simulation paused by operator.")

    def resume(self):
        """Resumes time-stepping."""
        self._is_paused = False
        self._log_event("SIMULATION_RESUMED", "Simulation resumed.")

    def is_paused(self) -> bool:
        """Returns True if the simulation clock is paused."""
        return self._is_paused

    def reset(self) -> NetworkState:
        """Restores the pristine warehouse baseline state and resets timer."""
        self.state.reset_to_baseline()
        self.state.health_score = calculate_health_score(self.state.simulated_values)
        self.state.alerts = detect_degradation_alerts(
            self.state.simulated_values,
            self.state.simulation_time,
            self.alert_thresholds,
        )
        self._is_paused = False
        self._log_event("SIMULATION_RESET", f"Reset state of {self.state.cell_id} to original warehouse baseline.")
        return self.state

    # -------------------------------------------------------------------------
    # 3. TIME-STEP SIMULATION UPDATE
    # -------------------------------------------------------------------------
    def step(self, delta_time: float = 1.0) -> NetworkState:
        """
        Advances the simulation forward by delta_time seconds.
        Evolves simulated values smoothly toward the target scenario steady-state.
        """
        if self._is_paused or delta_time <= 0.0:
            return self.state

        self.state.simulation_time += delta_time

        scen = self.state.scenario_name
        sev = self.state.severity

        # 1. Calculate Target Values
        target_kpis = calculate_scenario_target(
            baseline_values=self.state.baseline_values,
            scenario=scen,
            severity=sev,
        )

        # 2. Convergence Rate
        # In Recovery mode, converge at rate alpha; in degradation scenarios, shift at rate beta
        if scen == "NORMAL":
            rate = 1.0  # Instantaneous lock to baseline
        elif scen == "RECOVERY":
            rate = min(1.0, 0.25 * delta_time)
        else:
            rate = min(1.0, 0.35 * delta_time)

        # 3. Smooth State Update
        current = self.state.simulated_values
        new_values = {}
        for kpi, target in target_kpis.items():
            curr = float(current[kpi])
            updated = curr + rate * (target - curr)
            clamped = clamp_kpi_bounds(kpi, updated)
            new_values[kpi] = clamped

        # Write back to state
        self.state.latency_ms = round(new_values["latency_ms"], 2)
        self.state.throughput_mbps = round(new_values["throughput_mbps"], 2)
        self.state.packet_loss_pct = round(new_values["packet_loss_pct"], 3)
        self.state.call_drop_rate_pct = round(new_values["call_drop_rate_pct"], 3)
        self.state.signal_strength_dbm = round(new_values["signal_strength_dbm"], 2)
        self.state.handover_success_pct = round(new_values["handover_success_pct"], 2)
        self.state.active_connections = int(round(new_values["active_connections"]))

        # 4. Update Health Score & Alerts
        self.state.health_score = calculate_health_score(self.state.simulated_values)
        new_alerts = detect_degradation_alerts(
            self.state.simulated_values,
            self.state.simulation_time,
            self.alert_thresholds,
        )

        # Log new alert triggers
        prev_alert_types = {a["alert_type"] for a in self.state.alerts}
        for alert in new_alerts:
            if alert["alert_type"] not in prev_alert_types:
                self._log_event(
                    event_type="ALERT_TRIGGERED",
                    message=f"[{alert['alert_type']}] {alert['message']}",
                )

        self.state.alerts = new_alerts
        return self.state

    def update(self, delta_time: float = 1.0) -> NetworkState:
        """Alias for step(delta_time) matching standard game/simulation loop idioms."""
        return self.step(delta_time)

    # -------------------------------------------------------------------------
    # 4. EVENT LOGGING & COMPARISONS
    # -------------------------------------------------------------------------
    def _log_event(self, event_type: str, message: str):
        """Appends a timestamped simulation event to the in-memory event log."""
        self.event_log.append(
            {
                "simulation_time": round(self.state.simulation_time if self.state else 0.0, 2),
                "event_type": event_type,
                "cell_id": self.state.cell_id if self.state else self.default_cell_id,
                "region": self.state.region if self.state else "N/A",
                "technology": self.state.technology if self.state else "N/A",
                "scenario": self.state.scenario_name if self.state else "N/A",
                "severity": self.state.severity if self.state else "N/A",
                "message": message,
            }
        )

    def get_event_log(self) -> List[Dict[str, Any]]:
        """Returns the complete list of simulation events."""
        return list(self.event_log)

    def clear_event_log(self):
        """Clears the in-memory event log."""
        self.event_log.clear()

    def get_comparison(self) -> List[Dict[str, Any]]:
        """Returns delta comparison between baseline and currently simulated state."""
        return self.state.get_comparison()

    def evaluate_all_scenarios(self, severity: str = "MEDIUM") -> List[Dict[str, Any]]:
        """
        Evaluates NORMAL, CONGESTION, SIGNAL_DEGRADATION, and CELL_OVERLOAD
        against the current cell's baseline observation.
        Returns a comparative summary matrix for dashboard and analytical display.
        """
        scenarios_to_test = ["NORMAL", "CONGESTION", "SIGNAL_DEGRADATION", "CELL_OVERLOAD"]
        comparison_matrix = []

        for scen in scenarios_to_test:
            targets = calculate_scenario_target(
                baseline_values=self.state.baseline_values,
                scenario=scen,
                severity=severity,
            )
            score = calculate_health_score(targets)
            alerts = detect_degradation_alerts(targets, 0.0, self.alert_thresholds)

            comparison_matrix.append(
                {
                    "scenario": scen,
                    "severity": severity if scen != "NORMAL" else "NONE",
                    "latency_ms": round(targets["latency_ms"], 2),
                    "throughput_mbps": round(targets["throughput_mbps"], 2),
                    "packet_loss_pct": round(targets["packet_loss_pct"], 3),
                    "call_drop_rate_pct": round(targets["call_drop_rate_pct"], 3),
                    "signal_strength_dbm": round(targets["signal_strength_dbm"], 2),
                    "handover_success_pct": round(targets["handover_success_pct"], 2),
                    "active_connections": int(targets["active_connections"]),
                    "health_score": score,
                    "active_alerts_count": len(alerts),
                    "high_call_drop_alert": any(a["alert_type"] == "HIGH_CALL_DROP" for a in alerts),
                }
            )

        return comparison_matrix

    def get_topology_snapshot(self) -> Dict[str, Any]:
        """
        Exposes a structured 2D topology snapshot of the current simulated cell
        ready for rendering by future frontends.
        """
        return {
            "cell_id": self.state.cell_id,
            "region": self.state.region,
            "technology": self.state.technology,
            "timestamp": self.state.timestamp,
            "scenario": self.state.scenario_name,
            "severity": self.state.severity,
            "simulation_time": round(self.state.simulation_time, 2),
            "health_score": round(self.state.health_score, 1),
            "is_paused": self._is_paused,
            "metrics": self.state.simulated_values,
            "alerts": self.state.alerts,
            "event_count": len(self.event_log),
        }
