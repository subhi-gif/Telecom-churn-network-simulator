"""
Health Check Route
Verifies service availability and SQLite warehouse connectivity.
"""

from fastapi import APIRouter, Depends
import sqlite3
from backend.api.dependencies import get_db_connection

router = APIRouter(tags=["Health"])


@router.get("/health")
def get_health(conn: sqlite3.Connection = Depends(get_db_connection)):
    """
    Verifies service health and warehouse database connectivity.
    """
    cur = conn.cursor()
    cur.execute("SELECT 1;")
    cur.fetchone()

    payload = {
        "status": "ok",
        "service": "telecom-churn-network-api",
        "database": "connected",
    }
    return {
        **payload,
        "success": True,
        "data": payload,
    }
