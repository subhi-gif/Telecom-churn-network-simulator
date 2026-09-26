"""
Simulation Engine Routes
Exposes the in-memory Telecom Network Simulation Engine for live cell degradation testing,
state updates, baseline delta comparisons, and event logging.
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException
from backend.api.dependencies import get_simulation_engine
from backend.api.schemas import (
    ApiResponse,
    CellSelectRequest,
    ScenarioRequest,
    SimulationStateData,
    SimulationUpdateRequest,
)
from backend.simulation.engine import SimulationEngine
from backend.simulation.scenarios import VALID_SCENARIOS, VALID_SEVERITIES

router = APIRouter(prefix="/simulation", tags=["Simulation"])


def _format_state_response(engine: SimulationEngine) -> Dict[str, Any]:
    """Helper to format simulation state payload."""
    st = engine.state
    return {
        "simulation": True,
        "simulation_active": not engine.is_paused(),
        "cell": {
            "cell_id": st.cell_id,
            "region": st.region,
            "technology": st.technology,
            "timestamp": st.timestamp,
        },
        "scenario": st.scenario_name,
        "severity": st.severity,
        "simulation_time": round(st.simulation_time, 2),
        "baseline": st.baseline_values,
        "current": st.simulated_values,
        "health_score": round(st.health_score, 1),
        "alerts": st.alerts,
    }


@router.get("/state", response_model=ApiResponse[Dict[str, Any]])
def get_simulation_state(engine: SimulationEngine = Depends(get_simulation_engine)):
    """
    Returns the current in-memory operational state of the simulated cell,
    including baseline values, simulated values, health score, and active alerts.
    """
    return ApiResponse(success=True, data=_format_state_response(engine))


@router.post("/select-cell", response_model=ApiResponse[Dict[str, Any]])
def select_cell(
    req: CellSelectRequest,
    engine: SimulationEngine = Depends(get_simulation_engine),
):
    """
    Switches the simulation baseline to an authentic observation from warehouse.db.
    Returns HTTP 404 if the cell does not exist.
    """
    clean_id = req.cell_id.strip()
    try:
        engine.load_cell_baseline(clean_id)
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail={"code": "CELL_NOT_FOUND", "message": str(e)},
        )

    return ApiResponse(success=True, data=_format_state_response(engine))


@router.post("/scenario", response_model=ApiResponse[Dict[str, Any]])
def apply_scenario(
    req: ScenarioRequest,
    engine: SimulationEngine = Depends(get_simulation_engine),
):
    """
    Applies an operational scenario (NORMAL, CONGESTION, SIGNAL_DEGRADATION, CELL_OVERLOAD, RECOVERY)
    and severity (LOW, MEDIUM, HIGH) to the simulated cell.
    """
    scen = req.scenario.strip().upper()
    sev = req.severity.strip().upper()

    if scen not in VALID_SCENARIOS:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_SCENARIO",
                "message": f"Scenario '{req.scenario}' is invalid. Supported: {sorted(list(VALID_SCENARIOS))}",
            },
        )

    if sev not in VALID_SEVERITIES:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_SEVERITY",
                "message": f"Severity '{req.severity}' is invalid. Supported: {sorted(list(VALID_SEVERITIES))}",
            },
        )

    engine.apply_scenario(scen, sev)
    return ApiResponse(success=True, data=_format_state_response(engine))


@router.post("/update", response_model=ApiResponse[Dict[str, Any]])
def update_simulation(
    req: SimulationUpdateRequest,
    engine: SimulationEngine = Depends(get_simulation_engine),
):
    """
    Advances the simulation by delta_time seconds, evolving simulated telemetry
    smoothly toward the target scenario steady-state.
    """
    if req.delta_time <= 0.0 or req.delta_time > 60.0:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_DELTA_TIME",
                "message": f"delta_time must be strictly positive and <= 60.0 seconds. Received: {req.delta_time}",
            },
        )

    engine.update(req.delta_time)
    return ApiResponse(success=True, data=_format_state_response(engine))


@router.post("/pause", response_model=ApiResponse[Dict[str, Any]])
def pause_simulation(engine: SimulationEngine = Depends(get_simulation_engine)):
    """Pauses the simulation clock."""
    engine.pause()
    return ApiResponse(
        success=True,
        data={"simulation_active": False, "message": "Simulation paused by operator.", "simulation_time": round(engine.state.simulation_time, 2)},
    )


@router.post("/resume", response_model=ApiResponse[Dict[str, Any]])
def resume_simulation(engine: SimulationEngine = Depends(get_simulation_engine)):
    """Resumes the simulation clock."""
    engine.resume()
    return ApiResponse(
        success=True,
        data={"simulation_active": True, "message": "Simulation resumed.", "simulation_time": round(engine.state.simulation_time, 2)},
    )


@router.post("/reset", response_model=ApiResponse[Dict[str, Any]])
def reset_simulation(engine: SimulationEngine = Depends(get_simulation_engine)):
    """Restores the simulated cell to its pristine warehouse baseline."""
    engine.reset()
    return ApiResponse(success=True, data=_format_state_response(engine))


@router.get("/comparison", response_model=ApiResponse[List[Dict[str, Any]]])
def get_simulation_comparison(engine: SimulationEngine = Depends(get_simulation_engine)):
    """
    Returns delta comparison between baseline and currently simulated state
    for all 7 radio access KPIs.
    """
    comps = engine.get_comparison()
    return ApiResponse(success=True, data=comps)


@router.get("/events", response_model=ApiResponse[List[Dict[str, Any]]])
def get_simulation_events(engine: SimulationEngine = Depends(get_simulation_engine)):
    """Returns the in-memory chronological simulation audit log."""
    return ApiResponse(success=True, data=engine.get_event_log())


@router.delete("/events", response_model=ApiResponse[Dict[str, Any]])
def clear_simulation_events(engine: SimulationEngine = Depends(get_simulation_engine)):
    """Clears the in-memory simulation audit log."""
    engine.clear_event_log()
    return ApiResponse(success=True, data={"message": "In-memory simulation event log cleared."})
