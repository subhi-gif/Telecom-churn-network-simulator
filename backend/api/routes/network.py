"""
Network KPI Telemetry Routes
Exposes authentic historical observations and aggregate statistical summaries from FACT_NETWORK_KPI.
"""

from typing import List, Optional
import sqlite3
from fastapi import APIRouter, Depends, HTTPException, Query
from backend.api.dependencies import get_db_connection
from backend.api.schemas import (
    ApiResponse,
    NetworkMetricRange,
    NetworkObservation,
    NetworkSummaryData,
)

router = APIRouter(prefix="/network", tags=["Network"])


@router.get("/{cell_id}", response_model=ApiResponse[List[NetworkObservation]])
def get_cell_telemetry(
    cell_id: str,
    start_time: Optional[str] = Query(None, description="Start timestamp filter (YYYY-MM-DD HH:MM:SS)"),
    end_time: Optional[str] = Query(None, description="End timestamp filter (YYYY-MM-DD HH:MM:SS)"),
    limit: int = Query(100, ge=1, le=1000, description="Max observations to return (1-1000)"),
    conn: sqlite3.Connection = Depends(get_db_connection),
):
    """
    Returns actual time-series observations from FACT_NETWORK_KPI for a specific cell.
    Supports temporal filtering and safe query limits.
    """
    clean_id = cell_id.strip()
    cur = conn.cursor()

    # Verify cell existence
    cur.execute("SELECT cell_key FROM DIM_CELL WHERE cell_id = ?;", (clean_id,))
    if not cur.fetchone():
        raise HTTPException(
            status_code=404,
            detail={"code": "CELL_NOT_FOUND", "message": f"Cell '{cell_id}' not found in DIM_CELL dimension."},
        )

    conditions = ["c.cell_id = ?"]
    params = [clean_id]

    if start_time:
        conditions.append("t.timestamp >= ?")
        params.append(start_time.strip())

    if end_time:
        conditions.append("t.timestamp <= ?")
        params.append(end_time.strip())

    where_clause = " AND ".join(conditions)
    params.append(limit)

    sql = f"""
        SELECT 
            t.timestamp,
            r.region_name AS region,
            c.cell_id,
            tech.technology_name AS technology,
            f.latency_ms,
            f.throughput_mbps,
            f.packet_loss_pct,
            f.call_drop_rate_pct,
            f.signal_strength_dbm,
            f.handover_success_pct,
            f.active_connections
        FROM FACT_NETWORK_KPI f
        JOIN DIM_CELL c ON f.cell_key = c.cell_key
        JOIN DIM_REGION r ON f.region_key = r.region_key
        JOIN DIM_NETWORK_TECH tech ON f.technology_key = tech.technology_key
        JOIN DIM_TIME t ON f.time_key = t.time_key
        WHERE {where_clause}
        ORDER BY t.timestamp ASC
        LIMIT ?;
    """

    cur.execute(sql, params)
    rows = cur.fetchall()

    observations = [
        NetworkObservation(
            timestamp=row["timestamp"],
            region=row["region"],
            cell_id=row["cell_id"],
            technology=row["technology"],
            latency_ms=round(float(row["latency_ms"]), 2),
            throughput_mbps=round(float(row["throughput_mbps"]), 2),
            packet_loss_pct=round(float(row["packet_loss_pct"]), 3),
            call_drop_rate_pct=round(float(row["call_drop_rate_pct"]), 3),
            signal_strength_dbm=round(float(row["signal_strength_dbm"]), 2),
            handover_success_pct=round(float(row["handover_success_pct"]), 2),
            active_connections=int(row["active_connections"]),
        )
        for row in rows
    ]

    return ApiResponse(success=True, data=observations)


@router.get("/{cell_id}/summary", response_model=ApiResponse[NetworkSummaryData])
def get_cell_summary(
    cell_id: str,
    conn: sqlite3.Connection = Depends(get_db_connection),
):
    """
    Returns aggregated real warehouse KPIs for a specific cell, including averages, minimums,
    and maximums clearly labeled as warehouse historical records.
    """
    clean_id = cell_id.strip()
    cur = conn.cursor()

    # Verify cell existence
    cur.execute("SELECT cell_key FROM DIM_CELL WHERE cell_id = ?;", (clean_id,))
    if not cur.fetchone():
        raise HTTPException(
            status_code=404,
            detail={"code": "CELL_NOT_FOUND", "message": f"Cell '{cell_id}' not found in DIM_CELL dimension."},
        )

    sql = """
        SELECT 
            c.cell_id,
            r.region_name AS region,
            tech.technology_name AS technology,
            COUNT(*) AS observation_count,
            AVG(f.latency_ms) AS avg_lat,
            MIN(f.latency_ms) AS min_lat,
            MAX(f.latency_ms) AS max_lat,
            AVG(f.throughput_mbps) AS avg_tput,
            MIN(f.throughput_mbps) AS min_tput,
            MAX(f.throughput_mbps) AS max_tput,
            AVG(f.packet_loss_pct) AS avg_loss,
            MIN(f.packet_loss_pct) AS min_loss,
            MAX(f.packet_loss_pct) AS max_loss,
            AVG(f.call_drop_rate_pct) AS avg_drop,
            MIN(f.call_drop_rate_pct) AS min_drop,
            MAX(f.call_drop_rate_pct) AS max_drop,
            AVG(f.signal_strength_dbm) AS avg_sig,
            MIN(f.signal_strength_dbm) AS min_sig,
            MAX(f.signal_strength_dbm) AS max_sig,
            AVG(f.handover_success_pct) AS avg_ho,
            MIN(f.handover_success_pct) AS min_ho,
            MAX(f.handover_success_pct) AS max_ho,
            AVG(f.active_connections) AS avg_conn,
            MIN(f.active_connections) AS min_conn,
            MAX(f.active_connections) AS max_conn
        FROM FACT_NETWORK_KPI f
        JOIN DIM_CELL c ON f.cell_key = c.cell_key
        JOIN DIM_REGION r ON f.region_key = r.region_key
        JOIN DIM_NETWORK_TECH tech ON f.technology_key = tech.technology_key
        WHERE c.cell_id = ?
        GROUP BY c.cell_id, r.region_name, tech.technology_name;
    """

    cur.execute(sql, (clean_id,))
    row = cur.fetchone()

    if not row or int(row["observation_count"]) == 0:
        raise HTTPException(
            status_code=404,
            detail={"code": "NO_TELEMETRY", "message": f"No telemetry observations available for '{cell_id}'."},
        )

    summary = NetworkSummaryData(
        cell_id=row["cell_id"],
        region=row["region"],
        technology=row["technology"],
        observation_count=int(row["observation_count"]),
        data_source="warehouse_historical",
        average_latency_ms=round(float(row["avg_lat"]), 2),
        average_throughput_mbps=round(float(row["avg_tput"]), 2),
        average_packet_loss_pct=round(float(row["avg_loss"]), 3),
        average_call_drop_rate_pct=round(float(row["avg_drop"]), 3),
        average_signal_strength_dbm=round(float(row["avg_sig"]), 2),
        average_handover_success_pct=round(float(row["avg_ho"]), 2),
        average_active_connections=round(float(row["avg_conn"]), 1),
        metrics={
            "latency_ms": NetworkMetricRange(min=round(float(row["min_lat"]), 2), max=round(float(row["max_lat"]), 2), avg=round(float(row["avg_lat"]), 2)),
            "throughput_mbps": NetworkMetricRange(min=round(float(row["min_tput"]), 2), max=round(float(row["max_tput"]), 2), avg=round(float(row["avg_tput"]), 2)),
            "packet_loss_pct": NetworkMetricRange(min=round(float(row["min_loss"]), 3), max=round(float(row["max_loss"]), 3), avg=round(float(row["avg_loss"]), 3)),
            "call_drop_rate_pct": NetworkMetricRange(min=round(float(row["min_drop"]), 3), max=round(float(row["max_drop"]), 3), avg=round(float(row["avg_drop"]), 3)),
            "signal_strength_dbm": NetworkMetricRange(min=round(float(row["min_sig"]), 2), max=round(float(row["max_sig"]), 2), avg=round(float(row["avg_sig"]), 2)),
            "handover_success_pct": NetworkMetricRange(min=round(float(row["min_ho"]), 2), max=round(float(row["max_ho"]), 2), avg=round(float(row["avg_ho"]), 2)),
            "active_connections": NetworkMetricRange(min=float(row["min_conn"]), max=float(row["max_conn"]), avg=round(float(row["avg_conn"]), 1)),
        },
    )

    return ApiResponse(success=True, data=summary)
