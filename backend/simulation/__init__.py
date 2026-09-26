"""
Simulation Package Initialization
Exposes the core simulation engine, network state representation,
metrics/health calculation functions, and scenario configuration profiles.
"""

from backend.simulation.engine import SimulationEngine
from backend.simulation.metrics import (
    DEFAULT_ALERT_THRESHOLDS,
    calculate_health_score,
    detect_degradation_alerts,
)
from backend.simulation.network_state import (
    KPI_DISPLAY_NAMES,
    KPI_KEYS,
    NetworkState,
)
from backend.simulation.scenarios import (
    KPI_PHYSICAL_BOUNDS,
    SCENARIO_PROFILES,
    VALID_SCENARIOS,
    VALID_SEVERITIES,
    calculate_scenario_target,
    clamp_kpi_bounds,
)

__all__ = [
    "SimulationEngine",
    "NetworkState",
    "calculate_health_score",
    "detect_degradation_alerts",
    "DEFAULT_ALERT_THRESHOLDS",
    "SCENARIO_PROFILES",
    "VALID_SCENARIOS",
    "VALID_SEVERITIES",
    "KPI_PHYSICAL_BOUNDS",
    "clamp_kpi_bounds",
    "calculate_scenario_target",
    "KPI_KEYS",
    "KPI_DISPLAY_NAMES",
]
