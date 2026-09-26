"""
FastAPI Dependencies Module
Provides database connection access and shared singleton services (SimulationEngine).
"""

import sqlite3
from typing import Generator
from backend.olap.queries import get_default_db_path
from backend.simulation.engine import SimulationEngine

# Shared in-memory simulation engine singleton initialized with default warehouse cell
_SIMULATION_ENGINE_INSTANCE: SimulationEngine = None


def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """
    Yields an active SQLite database connection to warehouse.db with Row factory.
    Uses check_same_thread=False to support multi-threaded FastAPI async worker execution.
    Ensures safe, deterministic cleanup on request completion.
    """
    db_path = get_default_db_path()
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
    finally:
        conn.close()


def get_simulation_engine() -> SimulationEngine:
    """
    Returns the singleton SimulationEngine instance.
    Initializes on first call with authentic baseline Cell_0025.
    """
    global _SIMULATION_ENGINE_INSTANCE
    if _SIMULATION_ENGINE_INSTANCE is None:
        _SIMULATION_ENGINE_INSTANCE = SimulationEngine(default_cell_id="Cell_0025")
    return _SIMULATION_ENGINE_INSTANCE
