"""
Cell Inventory & Detail Routes
Exposes actual radio cell dimensions from warehouse.db with optional filtering.
"""

from typing import List, Optional
import sqlite3
from fastapi import APIRouter, Depends, HTTPException, Query
from backend.api.dependencies import get_db_connection
from backend.api.schemas import ApiResponse, CellDetail, CellItem

router = APIRouter(prefix="/cells", tags=["Cells"])


@router.get("", response_model=ApiResponse[List[CellItem]])
def list_cells(
    region: Optional[str] = Query(None, description="Filter by geographic region (North, South, East, West, Central)"),
    technology: Optional[str] = Query(None, description="Filter by radio technology (3G, 4G, 5G, LTE)"),
    conn: sqlite3.Connection = Depends(get_db_connection),
):
    """
    Returns real cells from the DIM_CELL star schema dimension,
    joined with region and technology from FACT_NETWORK_KPI.
    """
    cur = conn.cursor()

    conditions = []
    params = []

    if region:
        conditions.append("LOWER(r.region_name) = LOWER(?)")
        params.append(region.strip())

    if technology:
        conditions.append("LOWER(tech.technology_name) = LOWER(?)")
        params.append(technology.strip())

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    sql = f"""
        SELECT DISTINCT 
            c.cell_id, 
            r.region_name AS region, 
            tech.technology_name AS technology
        FROM FACT_NETWORK_KPI f
        JOIN DIM_CELL c ON f.cell_key = c.cell_key
        JOIN DIM_REGION r ON f.region_key = r.region_key
        JOIN DIM_NETWORK_TECH tech ON f.technology_key = tech.technology_key
        {where_clause}
        ORDER BY c.cell_id ASC;
    """

    cur.execute(sql, params)
    rows = cur.fetchall()

    cells = [
        CellItem(cell_id=row["cell_id"], region=row["region"], technology=row["technology"])
        for row in rows
    ]

    return ApiResponse(success=True, data=cells)


@router.get("/{cell_id}", response_model=ApiResponse[CellDetail])
def get_cell_detail(
    cell_id: str,
    conn: sqlite3.Connection = Depends(get_db_connection),
):
    """
    Returns authentic warehouse metadata, observation count, and time range for a specific cell.
    Returns HTTP 404 if the cell does not exist.
    """
    clean_id = cell_id.strip()
    cur = conn.cursor()

    # Verify cell exists
    cur.execute("SELECT cell_key, cell_id FROM DIM_CELL WHERE cell_id = ?;", (clean_id,))
    cell_row = cur.fetchone()
    if not cell_row:
        raise HTTPException(
            status_code=404,
            detail={"code": "CELL_NOT_FOUND", "message": f"Cell '{cell_id}' does not exist in the warehouse."},
        )

    # Query aggregate metadata
    sql = """
        SELECT 
            c.cell_id,
            r.region_name AS region,
            tech.technology_name AS technology,
            COUNT(*) AS observation_count,
            MIN(t.timestamp) AS start_time,
            MAX(t.timestamp) AS end_time
        FROM FACT_NETWORK_KPI f
        JOIN DIM_CELL c ON f.cell_key = c.cell_key
        JOIN DIM_REGION r ON f.region_key = r.region_key
        JOIN DIM_NETWORK_TECH tech ON f.technology_key = tech.technology_key
        JOIN DIM_TIME t ON f.time_key = t.time_key
        WHERE c.cell_id = ?
        GROUP BY c.cell_id, r.region_name, tech.technology_name;
    """
    cur.execute(sql, (clean_id,))
    row = cur.fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail={"code": "CELL_NO_DATA", "message": f"No observations found in warehouse for '{cell_id}'."},
        )

    detail = CellDetail(
        cell_id=row["cell_id"],
        region=row["region"],
        technology=row["technology"],
        available_observation_count=int(row["observation_count"]),
        time_range={"start_time": row["start_time"], "end_time": row["end_time"]},
    )

    return ApiResponse(success=True, data=detail)
