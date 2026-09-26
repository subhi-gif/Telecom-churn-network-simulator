"""
Simulation Metrics, Health Scoring, and Alerting Module
Implements the transparent 'Simulation Health Score' (0-100) formula and configurable
telemetry degradation alert detectors.
"""

from typing import Any, Dict, List, Optional


# Default configurable alert thresholds
DEFAULT_ALERT_THRESHOLDS = {
    "call_drop_rate_pct": 2.0,       # Analytical threshold from project design (> 2.0%)
    "latency_ms": 80.0,              # High latency threshold (> 80 ms)
    "packet_loss_pct": 3.0,          # High packet loss threshold (> 3.0%)
    "handover_success_pct": 90.0,    # Low handover success floor (< 90.0%)
}


def calculate_health_score(kpis: Dict[str, Any]) -> float:
    """
    Computes a transparent composite 'Simulation Health Score' (0 to 100).

    Formula Architecture:
        Health Score = 100 - (P_call_drop + P_packet_loss + P_latency + P_signal + P_handover)

        Components:
        1. Call Drop Penalty (P_call_drop, max 30 pts):
           P_call_drop = min(30.0, call_drop_rate_pct * 10.0)
           (A 3% call drop rate subtracts all 30 points)

        2. Packet Loss Penalty (P_packet_loss, max 20 pts):
           P_packet_loss = min(20.0, packet_loss_pct * 4.0)
           (A 5% packet loss subtracts all 20 points)

        3. Latency Penalty (P_latency, max 20 pts):
           P_latency = min(20.0, max(0.0, (latency_ms - 20.0) * 0.25))
           (Nominal latency <= 20ms incurs 0 penalty; 100ms incurs 20 points)

        4. Signal Attenuation Penalty (P_signal, max 15 pts):
           P_signal = min(15.0, max(0.0, (-70.0 - signal_strength_dbm) * 0.5))
           (Signal >= -70 dBm incurs 0 penalty; -100 dBm incurs 15 points)

        5. Handover Impairment Penalty (P_handover, max 15 pts):
           P_handover = min(15.0, max(0.0, (96.0 - handover_success_pct) * 1.5))
           (Handover >= 96% incurs 0 penalty; <= 86% incurs 15 points)

    Returns:
        float: Bounded between 0.0 (catastrophic failure) and 100.0 (flawless health).
    """
    call_drop = float(kpis.get("call_drop_rate_pct", 0.0))
    packet_loss = float(kpis.get("packet_loss_pct", 0.0))
    latency = float(kpis.get("latency_ms", 20.0))
    signal = float(kpis.get("signal_strength_dbm", -55.0))
    handover = float(kpis.get("handover_success_pct", 98.0))

    p_call_drop = min(30.0, max(0.0, call_drop * 10.0))
    p_packet_loss = min(20.0, max(0.0, packet_loss * 4.0))
    p_latency = min(20.0, max(0.0, (latency - 20.0) * 0.25))
    p_signal = min(15.0, max(0.0, (-70.0 - signal) * 0.5))
    p_handover = min(15.0, max(0.0, (96.0 - handover) * 1.5))

    total_penalty = p_call_drop + p_packet_loss + p_latency + p_signal + p_handover
    score = max(0.0, min(100.0, 100.0 - total_penalty))
    return round(score, 1)


def detect_degradation_alerts(
    kpis: Dict[str, Any],
    simulation_time: float = 0.0,
    thresholds: Optional[Dict[str, float]] = None,
) -> List[Dict[str, Any]]:
    """
    Evaluates simulated telemetry against analytical degradation thresholds.
    Labels every alert explicitly as a 'SIMULATED CONDITION'.

    Parameters:
        kpis: Current simulated KPI readings.
        simulation_time: Elapsed simulation time in seconds.
        thresholds: Optional custom threshold overrides.

    Returns:
        List[Dict[str, Any]]: Generated degradation alerts.
    """
    active_thresh = dict(DEFAULT_ALERT_THRESHOLDS)
    if thresholds:
        active_thresh.update(thresholds)

    alerts = []

    # 1. High Call Drop Alert (> threshold, default 2.0%)
    call_drop = float(kpis.get("call_drop_rate_pct", 0.0))
    cd_thresh = active_thresh["call_drop_rate_pct"]
    if call_drop > cd_thresh:
        sev = "CRITICAL" if call_drop >= (cd_thresh * 2.5) else "WARNING"
        alerts.append(
            {
                "alert_type": "HIGH_CALL_DROP",
                "severity": sev,
                "current_value": round(call_drop, 3),
                "threshold": cd_thresh,
                "simulation_time": round(simulation_time, 2),
                "condition_type": "SIMULATED CONDITION",
                "message": f"Simulated call drop rate ({call_drop:.2f}%) exceeds analytical threshold ({cd_thresh:.1f}%).",
            }
        )

    # 2. High Latency Alert (> threshold, default 80 ms)
    latency = float(kpis.get("latency_ms", 0.0))
    lat_thresh = active_thresh["latency_ms"]
    if latency > lat_thresh:
        sev = "CRITICAL" if latency >= (lat_thresh * 2.0) else "WARNING"
        alerts.append(
            {
                "alert_type": "HIGH_LATENCY",
                "severity": sev,
                "current_value": round(latency, 2),
                "threshold": lat_thresh,
                "simulation_time": round(simulation_time, 2),
                "condition_type": "SIMULATED CONDITION",
                "message": f"Simulated round-trip latency ({latency:.1f} ms) exceeds operational ceiling ({lat_thresh:.0f} ms).",
            }
        )

    # 3. High Packet Loss Alert (> threshold, default 3.0%)
    packet_loss = float(kpis.get("packet_loss_pct", 0.0))
    loss_thresh = active_thresh["packet_loss_pct"]
    if packet_loss > loss_thresh:
        sev = "CRITICAL" if packet_loss >= (loss_thresh * 2.0) else "WARNING"
        alerts.append(
            {
                "alert_type": "HIGH_PACKET_LOSS",
                "severity": sev,
                "current_value": round(packet_loss, 3),
                "threshold": loss_thresh,
                "simulation_time": round(simulation_time, 2),
                "condition_type": "SIMULATED CONDITION",
                "message": f"Simulated IP packet loss ({packet_loss:.2f}%) exceeds tolerance ({loss_thresh:.1f}%).",
            }
        )

    # 4. Low Handover Success Alert (< threshold, default 90.0%)
    handover = float(kpis.get("handover_success_pct", 100.0))
    ho_thresh = active_thresh["handover_success_pct"]
    if handover < ho_thresh:
        sev = "CRITICAL" if handover < (ho_thresh - 10.0) else "WARNING"
        alerts.append(
            {
                "alert_type": "LOW_HANDOVER_SUCCESS",
                "severity": sev,
                "current_value": round(handover, 2),
                "threshold": ho_thresh,
                "simulation_time": round(simulation_time, 2),
                "condition_type": "SIMULATED CONDITION",
                "message": f"Simulated inter-cell handover success ({handover:.1f}%) dropped below threshold ({ho_thresh:.0f}%).",
            }
        )

    return alerts
