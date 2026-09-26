"""
Simulation Scenarios and Parameter Matrices Module
Defines configurable degradation profiles, severity multipliers, physical clipping bounds,
and state transition functions for telecom radio access network simulation.
"""

from typing import Any, Dict, Optional, Tuple


VALID_SCENARIOS = {
    "NORMAL",
    "CONGESTION",
    "SIGNAL_DEGRADATION",
    "CELL_OVERLOAD",
    "RECOVERY",
}

VALID_SEVERITIES = {"LOW", "MEDIUM", "HIGH"}

# Physical / Operational telemetry limits based on cellular domain standards and warehouse statistics
KPI_PHYSICAL_BOUNDS = {
    "latency_ms": (1.0, 1000.0),          # Latency cannot fall below 1ms or exceed 1000ms
    "throughput_mbps": (0.0, 1200.0),     # Max practical 5G downlink cell capacity
    "packet_loss_pct": (0.0, 100.0),      # Percentage bounds
    "call_drop_rate_pct": (0.0, 100.0),   # Percentage bounds
    "signal_strength_dbm": (-120.0, -35.0), # RF receiver sensitivity floor to saturation ceiling
    "handover_success_pct": (0.0, 100.0), # Percentage bounds
    "active_connections": (0, 5000),      # Max connected UEs per cell sector
}


def clamp_kpi_bounds(metric_key: str, value: float) -> float:
    """Clamps a simulated metric value to its documented physical/operational boundary."""
    if metric_key in KPI_PHYSICAL_BOUNDS:
        min_val, max_val = KPI_PHYSICAL_BOUNDS[metric_key]
        return max(min_val, min(max_val, value))
    return value


# -----------------------------------------------------------------------------
# SCENARIO DEGRADATION MATRICES
# -----------------------------------------------------------------------------
# Each matrix defines:
#   - multipliers (ratio applied to baseline value)
#   - additive_deltas (absolute offset added to baseline value)
SCENARIO_PROFILES = {
    "NORMAL": {
        "LOW": {"multipliers": {}, "additive_deltas": {}},
        "MEDIUM": {"multipliers": {}, "additive_deltas": {}},
        "HIGH": {"multipliers": {}, "additive_deltas": {}},
    },
    "CONGESTION": {
        # Increasing user traffic and RF queue saturation
        "LOW": {
            "multipliers": {
                "active_connections": 1.30,      # +30% users
                "latency_ms": 1.25,              # +25% latency
                "throughput_mbps": 0.85,         # -15% throughput
                "handover_success_pct": 0.985,   # -1.5% handover success
            },
            "additive_deltas": {
                "packet_loss_pct": 0.50,         # +0.5% packet loss
                "call_drop_rate_pct": 0.30,      # +0.3% drop rate
                "signal_strength_dbm": 0.0,
            },
        },
        "MEDIUM": {
            "multipliers": {
                "active_connections": 1.75,      # +75% users
                "latency_ms": 1.65,              # +65% latency
                "throughput_mbps": 0.65,         # -35% throughput
                "handover_success_pct": 0.96,    # -4.0% handover success
            },
            "additive_deltas": {
                "packet_loss_pct": 1.80,         # +1.8% packet loss
                "call_drop_rate_pct": 0.95,      # +0.95% drop rate
                "signal_strength_dbm": -1.5,
            },
        },
        "HIGH": {
            "multipliers": {
                "active_connections": 2.50,      # +150% users
                "latency_ms": 2.40,              # +140% latency
                "throughput_mbps": 0.40,         # -60% throughput
                "handover_success_pct": 0.91,    # -9.0% handover success
            },
            "additive_deltas": {
                "packet_loss_pct": 4.50,         # +4.5% packet loss
                "call_drop_rate_pct": 2.40,      # +2.4% drop rate (triggers HIGH_CALL_DROP)
                "signal_strength_dbm": -3.0,
            },
        },
    },
    "SIGNAL_DEGRADATION": {
        # RF path loss, foliage attenuation, or physical blockage
        "LOW": {
            "multipliers": {
                "throughput_mbps": 0.88,
                "latency_ms": 1.20,
                "handover_success_pct": 0.97,
            },
            "additive_deltas": {
                "signal_strength_dbm": -10.0,    # -10 dBm signal drop
                "packet_loss_pct": 1.20,         # +1.2% loss
                "call_drop_rate_pct": 0.50,      # +0.5% drops
                "active_connections": 0,
            },
        },
        "MEDIUM": {
            "multipliers": {
                "throughput_mbps": 0.65,
                "latency_ms": 1.60,
                "handover_success_pct": 0.92,
            },
            "additive_deltas": {
                "signal_strength_dbm": -22.0,    # -22 dBm signal drop
                "packet_loss_pct": 3.50,         # +3.5% loss (triggers HIGH_PACKET_LOSS)
                "call_drop_rate_pct": 1.50,      # +1.5% drops
                "active_connections": -15,       # users disconnecting due to poor RF
            },
        },
        "HIGH": {
            "multipliers": {
                "throughput_mbps": 0.35,
                "latency_ms": 2.50,
                "handover_success_pct": 0.82,
            },
            "additive_deltas": {
                "signal_strength_dbm": -38.0,    # -38 dBm severe fading
                "packet_loss_pct": 8.00,         # +8.0% loss
                "call_drop_rate_pct": 3.80,      # +3.8% drops (triggers HIGH_CALL_DROP)
                "active_connections": -40,
            },
        },
    },
    "CELL_OVERLOAD": {
        # Severe capacity saturation / mass event traffic surge
        "LOW": {
            "multipliers": {
                "active_connections": 2.00,      # Double active load
                "latency_ms": 1.80,
                "throughput_mbps": 0.60,
                "handover_success_pct": 0.94,
            },
            "additive_deltas": {
                "packet_loss_pct": 2.20,
                "call_drop_rate_pct": 1.10,
                "signal_strength_dbm": -2.0,
            },
        },
        "MEDIUM": {
            "multipliers": {
                "active_connections": 3.50,      # 3.5x active users
                "latency_ms": 3.50,
                "throughput_mbps": 0.30,         # Severe throughput collapse
                "handover_success_pct": 0.88,
            },
            "additive_deltas": {
                "packet_loss_pct": 6.50,
                "call_drop_rate_pct": 3.20,      # Triggers HIGH_CALL_DROP
                "signal_strength_dbm": -5.0,
            },
        },
        "HIGH": {
            "multipliers": {
                "active_connections": 6.00,      # 6x active users
                "latency_ms": 8.00,              # Massive latency spike (>100ms)
                "throughput_mbps": 0.10,         # 90% throughput collapse
                "handover_success_pct": 0.75,    # 25% handover failure
            },
            "additive_deltas": {
                "packet_loss_pct": 16.00,        # Severe packet drop
                "call_drop_rate_pct": 10.50,     # Critical drop rate
                "signal_strength_dbm": -8.0,
            },
        },
    },
}


def calculate_scenario_target(
    baseline_values: Dict[str, Any],
    scenario: str,
    severity: str = "MEDIUM",
) -> Dict[str, float]:
    """
    Computes the target steady-state simulated values for a given scenario and severity.
    Applies documented multipliers, additive deltas, and physical boundary clamping.
    """
    scen = scenario.strip().upper()
    sev = severity.strip().upper()

    if scen not in VALID_SCENARIOS:
        raise ValueError(f"Unknown scenario '{scenario}'. Valid scenarios: {sorted(list(VALID_SCENARIOS))}")
    if sev not in VALID_SEVERITIES:
        raise ValueError(f"Unknown severity '{severity}'. Valid severities: {sorted(list(VALID_SEVERITIES))}")

    if scen == "NORMAL" or scen == "RECOVERY":
        # Target for Normal and full Recovery is the baseline itself
        return {k: float(v) for k, v in baseline_values.items()}

    profile = SCENARIO_PROFILES[scen][sev]
    multipliers = profile["multipliers"]
    deltas = profile["additive_deltas"]

    target_values = {}
    for kpi, base_val in baseline_values.items():
        val = float(base_val)

        # Apply multiplier if specified
        if kpi in multipliers:
            val = val * multipliers[kpi]

        # Apply additive delta if specified
        if kpi in deltas:
            val = val + deltas[kpi]

        # Apply boundary clamping
        clamped = clamp_kpi_bounds(kpi, val)
        target_values[kpi] = clamped

    return target_values
