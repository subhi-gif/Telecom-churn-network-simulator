"""
Pydantic Schemas and Response Models for Telecom API
Defines input validation models and uniform API response envelopes.
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


# -----------------------------------------------------------------------------
# UNIFORM RESPONSE ENVELOPES
# -----------------------------------------------------------------------------
class ApiResponse(BaseModel, Generic[T]):
    """Standard success response wrapper."""
    success: bool = True
    data: T


class ErrorDetail(BaseModel):
    """Structured error descriptor."""
    code: str
    message: str


class ApiErrorResponse(BaseModel):
    """Standard error response wrapper."""
    success: bool = False
    error: ErrorDetail


# -----------------------------------------------------------------------------
# HEALTH SCHEMAS
# -----------------------------------------------------------------------------
class HealthData(BaseModel):
    status: str = "ok"
    service: str = "telecom-churn-network-api"
    database: str = "connected"


# -----------------------------------------------------------------------------
# CELL SCHEMAS
# -----------------------------------------------------------------------------
class CellItem(BaseModel):
    cell_id: str
    region: str
    technology: str


class CellDetail(BaseModel):
    cell_id: str
    region: str
    technology: str
    available_observation_count: int
    time_range: Dict[str, Optional[str]]


# -----------------------------------------------------------------------------
# NETWORK KPI SCHEMAS
# -----------------------------------------------------------------------------
class NetworkObservation(BaseModel):
    timestamp: str
    region: str
    cell_id: str
    technology: str
    latency_ms: float
    throughput_mbps: float
    packet_loss_pct: float
    call_drop_rate_pct: float
    signal_strength_dbm: float
    handover_success_pct: float
    active_connections: int


class NetworkMetricRange(BaseModel):
    min: float
    max: float
    avg: float


class NetworkSummaryData(BaseModel):
    cell_id: str
    region: str
    technology: str
    observation_count: int
    data_source: str = "warehouse_historical"
    average_latency_ms: float
    average_throughput_mbps: float
    average_packet_loss_pct: float
    average_call_drop_rate_pct: float
    average_signal_strength_dbm: float
    average_handover_success_pct: float
    average_active_connections: float
    metrics: Dict[str, NetworkMetricRange]


# -----------------------------------------------------------------------------
# SIMULATION REQUEST & RESPONSE SCHEMAS
# -----------------------------------------------------------------------------
class CellSelectRequest(BaseModel):
    cell_id: str = Field(..., min_length=1, max_length=50, description="Warehouse cell identifier (e.g. Cell_0025)")


class ScenarioRequest(BaseModel):
    scenario: str = Field(..., description="Simulation scenario (NORMAL, CONGESTION, SIGNAL_DEGRADATION, CELL_OVERLOAD, RECOVERY)")
    severity: str = Field("MEDIUM", description="Scenario severity (LOW, MEDIUM, HIGH)")


class SimulationUpdateRequest(BaseModel):
    delta_time: float = Field(1.0, gt=0.0, le=60.0, description="Elapsed time step in seconds (0.0 < delta_time <= 60.0)")


class SimulationStateData(BaseModel):
    simulation: bool = True
    simulation_active: bool
    cell: Dict[str, Any]
    scenario: str
    severity: str
    simulation_time: float
    baseline: Dict[str, Any]
    current: Dict[str, Any]
    health_score: float
    alerts: List[Dict[str, Any]]
