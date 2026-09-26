"""
Network State Representation Module
Defines the NetworkState data structure encapsulating real warehouse baseline parameters,
dynamic simulated telemetry, health scores, active alerts, and comparison utilities.
"""

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


KPI_KEYS = [
    "latency_ms",
    "throughput_mbps",
    "packet_loss_pct",
    "call_drop_rate_pct",
    "signal_strength_dbm",
    "handover_success_pct",
    "active_connections",
]

KPI_DISPLAY_NAMES = {
    "latency_ms": "Latency (ms)",
    "throughput_mbps": "Throughput (Mbps)",
    "packet_loss_pct": "Packet Loss (%)",
    "call_drop_rate_pct": "Call Drop Rate (%)",
    "signal_strength_dbm": "Signal Strength (dBm)",
    "handover_success_pct": "Handover Success (%)",
    "active_connections": "Active Connections",
}


@dataclass
class NetworkState:
    """
    Represents the operational state of a network cell during simulation.
    Preserves an immutable copy of warehouse baseline observations alongside dynamic simulated KPIs.
    """

    # Topological & Geographical Context (from warehouse)
    region: str
    cell_id: str
    technology: str
    timestamp: str

    # Current Simulated Telemetry Values
    latency_ms: float
    throughput_mbps: float
    packet_loss_pct: float
    call_drop_rate_pct: float
    signal_strength_dbm: float
    handover_success_pct: float
    active_connections: int

    # Simulation Metadata
    scenario_name: str = "NORMAL"
    severity: str = "LOW"
    simulation_time: float = 0.0  # Elapsed simulation time in seconds
    health_score: float = 100.0   # Simulation Health Score (0-100)
    alerts: List[Dict[str, Any]] = field(default_factory=list)

    # Immutable Reference Baseline (set once upon initialization)
    baseline_values: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # If baseline_values is empty, capture the initial state as immutable baseline
        if not self.baseline_values:
            self.baseline_values = {
                "latency_ms": round(float(self.latency_ms), 2),
                "throughput_mbps": round(float(self.throughput_mbps), 2),
                "packet_loss_pct": round(float(self.packet_loss_pct), 3),
                "call_drop_rate_pct": round(float(self.call_drop_rate_pct), 3),
                "signal_strength_dbm": round(float(self.signal_strength_dbm), 2),
                "handover_success_pct": round(float(self.handover_success_pct), 2),
                "active_connections": int(self.active_connections),
            }
        else:
            # Ensure it is a decoupled deep copy
            self.baseline_values = deepcopy(self.baseline_values)

    @property
    def simulated_values(self) -> Dict[str, Any]:
        """Returns dictionary of currently simulated KPI measurements."""
        return {
            "latency_ms": round(float(self.latency_ms), 2),
            "throughput_mbps": round(float(self.throughput_mbps), 2),
            "packet_loss_pct": round(float(self.packet_loss_pct), 3),
            "call_drop_rate_pct": round(float(self.call_drop_rate_pct), 3),
            "signal_strength_dbm": round(float(self.signal_strength_dbm), 2),
            "handover_success_pct": round(float(self.handover_success_pct), 2),
            "active_connections": int(self.active_connections),
        }

    def reset_to_baseline(self):
        """Restores simulated KPI values directly from the immutable baseline."""
        self.latency_ms = float(self.baseline_values["latency_ms"])
        self.throughput_mbps = float(self.baseline_values["throughput_mbps"])
        self.packet_loss_pct = float(self.baseline_values["packet_loss_pct"])
        self.call_drop_rate_pct = float(self.baseline_values["call_drop_rate_pct"])
        self.signal_strength_dbm = float(self.baseline_values["signal_strength_dbm"])
        self.handover_success_pct = float(self.baseline_values["handover_success_pct"])
        self.active_connections = int(self.baseline_values["active_connections"])

        self.scenario_name = "NORMAL"
        self.severity = "LOW"
        self.simulation_time = 0.0
        self.alerts = []

    def get_comparison(self) -> List[Dict[str, Any]]:
        """
        Calculates absolute and percentage deltas between baseline and simulated values.
        
        Returns:
            List[Dict[str, Any]]: Comparison rows suitable for tabular display or JSON serialization.
        """
        comparisons = []
        sim = self.simulated_values

        for kpi in KPI_KEYS:
            base_val = self.baseline_values[kpi]
            sim_val = sim[kpi]
            abs_diff = round(sim_val - base_val, 3)

            # Avoid division by zero
            if base_val != 0.0:
                pct_diff = round((abs_diff / abs(base_val)) * 100.0, 2)
            else:
                pct_diff = 0.0 if abs_diff == 0.0 else (100.0 if abs_diff > 0 else -100.0)

            comparisons.append(
                {
                    "metric_key": kpi,
                    "metric_name": KPI_DISPLAY_NAMES[kpi],
                    "baseline": base_val,
                    "simulated": sim_val,
                    "absolute_difference": abs_diff,
                    "percentage_difference": pct_diff,
                }
            )

        return comparisons

    def to_dict(self) -> Dict[str, Any]:
        """Returns complete serializable dictionary representation of the network state."""
        return {
            "cell_id": self.cell_id,
            "region": self.region,
            "technology": self.technology,
            "timestamp": self.timestamp,
            "scenario": self.scenario_name,
            "severity": self.severity,
            "simulation_time": round(self.simulation_time, 2),
            "health_score": round(self.health_score, 1),
            "baseline_values": deepcopy(self.baseline_values),
            "simulated_values": self.simulated_values,
            "comparisons": self.get_comparison(),
            "alerts": deepcopy(self.alerts),
        }
