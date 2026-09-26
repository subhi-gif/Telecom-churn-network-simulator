"""
OLAP Multidimensional Analysis Routes
Exposes analytical Roll-up, Drill-down, Slice, Dice, and Summary operations
directly calling backend/olap without duplicating SQL logic.
"""

from typing import Any, Dict, Optional
import sqlite3
from fastapi import APIRouter, Depends, HTTPException, Query
from backend.api.dependencies import get_db_connection
from backend.api.schemas import ApiResponse
from backend.olap import (
    CustomerOLAP,
    NetworkOLAP,
    get_customer_dice,
    get_customer_drilldown,
    get_customer_rollup,
    get_customer_slice,
    get_customer_summary,
    get_high_call_drop_cells,
    get_network_dice,
    get_network_drilldown,
    get_network_rollup,
    get_network_slice,
    get_network_summary,
)

router = APIRouter(prefix="/olap", tags=["OLAP"])


# -----------------------------------------------------------------------------
# CUSTOMER OLAP ROUTES
# -----------------------------------------------------------------------------
@router.get("/customer/summary", response_model=ApiResponse[Dict[str, Any]])
def customer_summary(conn: sqlite3.Connection = Depends(get_db_connection)):
    """Returns high-level aggregate KPIs across the Customer Churn Mart."""
    data = get_customer_summary(conn_or_path=conn)
    return ApiResponse(success=True, data=data)


@router.get("/customer/rollup", response_model=ApiResponse[Dict[str, Any]])
def customer_rollup(
    group_by: str = Query("contract", description="Dimension to aggregate along (contract, internet_service, payment_method, tenure_band)"),
    conn: sqlite3.Connection = Depends(get_db_connection),
):
    """Executes customer roll-up aggregation along a specified dimension."""
    data = get_customer_rollup(group_by=group_by, conn_or_path=conn)
    if data.get("status") == "error":
        raise HTTPException(status_code=400, detail={"code": "INVALID_DIMENSION", "message": data.get("message")})
    return ApiResponse(success=True, data=data)


@router.get("/customer/drilldown", response_model=ApiResponse[Dict[str, Any]])
def customer_drilldown(
    tenure_band: str = Query("0-12 months", description="Tenure band to drill into by contract type"),
    conn: sqlite3.Connection = Depends(get_db_connection),
):
    """Executes customer drill-down from tenure band into contract distribution."""
    data = get_customer_drilldown(tenure_band=tenure_band, conn_or_path=conn)
    if data.get("status") == "error":
        raise HTTPException(status_code=400, detail={"code": "INVALID_TENURE_BAND", "message": data.get("message")})
    return ApiResponse(success=True, data=data)


@router.get("/customer/slice", response_model=ApiResponse[Dict[str, Any]])
def customer_slice(
    dimension: str = Query("contract", description="Slice dimension (contract, internet_service, payment_method, tenure_band)"),
    value: str = Query("Month-to-month", description="Slice predicate value"),
    conn: sqlite3.Connection = Depends(get_db_connection),
):
    """Executes a single-dimension slice on the customer star schema."""
    data = get_customer_slice(dimension=dimension, value=value, conn_or_path=conn)
    if data.get("status") == "error":
        raise HTTPException(status_code=400, detail={"code": "INVALID_SLICE", "message": data.get("message")})
    return ApiResponse(success=True, data=data)


@router.get("/customer/dice", response_model=ApiResponse[Dict[str, Any]])
def customer_dice(
    contract: Optional[str] = Query(None, description="Contract filter"),
    internet_service: Optional[str] = Query(None, description="Internet service filter"),
    payment_method: Optional[str] = Query(None, description="Payment method filter"),
    tenure_band: Optional[str] = Query(None, description="Tenure band filter"),
    conn: sqlite3.Connection = Depends(get_db_connection),
):
    """Executes multi-dimensional dice filtering across customer dimensions."""
    filters = {}
    if contract:
        filters["contract"] = contract
    if internet_service:
        filters["internet_service"] = internet_service
    if payment_method:
        filters["payment_method"] = payment_method
    if tenure_band:
        filters["tenure_band"] = tenure_band

    data = get_customer_dice(filters=filters, conn_or_path=conn)
    if data.get("status") == "error":
        raise HTTPException(status_code=400, detail={"code": "INVALID_DICE", "message": data.get("message")})
    return ApiResponse(success=True, data=data)


# -----------------------------------------------------------------------------
# NETWORK OLAP ROUTES
# -----------------------------------------------------------------------------
@router.get("/network/summary", response_model=ApiResponse[Dict[str, Any]])
def network_summary(conn: sqlite3.Connection = Depends(get_db_connection)):
    """Returns high-level aggregate network KPIs across FACT_NETWORK_KPI."""
    data = get_network_summary(conn_or_path=conn)
    return ApiResponse(success=True, data=data)


@router.get("/network/rollup", response_model=ApiResponse[Dict[str, Any]])
def network_rollup(
    level: str = Query("hour", description="Temporal or categorical rollup level (minute, hour, region, technology)"),
    conn: sqlite3.Connection = Depends(get_db_connection),
):
    """Executes network roll-up along temporal or categorical hierarchies."""
    data = get_network_rollup(level=level, conn_or_path=conn)
    if data.get("status") == "error":
        raise HTTPException(status_code=400, detail={"code": "INVALID_LEVEL", "message": data.get("message")})
    return ApiResponse(success=True, data=data)


@router.get("/network/drilldown", response_model=ApiResponse[Dict[str, Any]])
def network_drilldown(
    region: str = Query("Central", description="Region to drill down into cells"),
    cell_id: Optional[str] = Query(None, description="Optional cell filter within region"),
    conn: sqlite3.Connection = Depends(get_db_connection),
):
    """Executes network drill-down from region down to individual cell sector telemetry."""
    data = get_network_drilldown(region=region, cell_id=cell_id, conn_or_path=conn)
    if data.get("status") == "error":
        raise HTTPException(status_code=400, detail={"code": "INVALID_REGION", "message": data.get("message")})
    return ApiResponse(success=True, data=data)


@router.get("/network/slice", response_model=ApiResponse[Dict[str, Any]])
def network_slice(
    dimension: str = Query("region", description="Slice dimension (region, technology, cell_id)"),
    value: str = Query("Central", description="Slice predicate value"),
    conn: sqlite3.Connection = Depends(get_db_connection),
):
    """Executes a single-dimension slice across the network performance mart."""
    data = get_network_slice(dimension=dimension, value=value, conn_or_path=conn)
    if data.get("status") == "error":
        raise HTTPException(status_code=400, detail={"code": "INVALID_SLICE", "message": data.get("message")})
    return ApiResponse(success=True, data=data)


@router.get("/network/dice", response_model=ApiResponse[Dict[str, Any]])
def network_dice(
    region: Optional[str] = Query(None, description="Region filter"),
    technology: Optional[str] = Query(None, description="Technology filter"),
    start_time: Optional[str] = Query(None, description="Start timestamp filter"),
    end_time: Optional[str] = Query(None, description="End timestamp filter"),
    conn: sqlite3.Connection = Depends(get_db_connection),
):
    """Executes multi-dimensional dice filtering across network dimensions."""
    filters = {}
    if region:
        filters["region"] = region
    if technology:
        filters["technology"] = technology
    if start_time:
        filters["start_time"] = start_time
    if end_time:
        filters["end_time"] = end_time

    data = get_network_dice(filters=filters, conn_or_path=conn)
    if data.get("status") == "error":
        raise HTTPException(status_code=400, detail={"code": "INVALID_DICE", "message": data.get("message")})
    return ApiResponse(success=True, data=data)


@router.get("/network/high-call-drop", response_model=ApiResponse[Dict[str, Any]])
def network_high_call_drop(
    threshold: float = Query(2.0, ge=0.0, le=100.0, description="Call drop rate threshold (%)"),
    conn: sqlite3.Connection = Depends(get_db_connection),
):
    """Analytical query identifying cell sectors with average call drop rates exceeding threshold."""
    data = get_high_call_drop_cells(threshold=threshold, conn_or_path=conn)
    return ApiResponse(success=True, data=data)
