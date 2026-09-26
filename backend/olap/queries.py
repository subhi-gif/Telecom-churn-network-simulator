"""
OLAP Query Engine & Schema Mapping Utilities
Provides parameterized SQL templates, domain validations, connection handling,
and safe query execution for the Customer Churn Mart and Network Performance Mart.
"""

import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Union

# -----------------------------------------------------------------------------
# DOMAIN WHITELISTS (Derived from authoritative warehouse schemas and ETL rules)
# -----------------------------------------------------------------------------
VALID_CONTRACTS = {"Month-to-month", "One year", "Two year"}
VALID_INTERNET_SERVICES = {"DSL", "Fiber optic", "No"}
VALID_PAYMENT_METHODS = {
    "Electronic check",
    "Mailed check",
    "Bank transfer (automatic)",
    "Credit card (automatic)",
}
VALID_TENURE_BANDS = {
    "0-12 months",
    "13-24 months",
    "25-48 months",
    "49-72 months",
}
VALID_REGIONS = {"Central", "East", "North", "South", "West"}
VALID_TECHNOLOGIES = {"LTE", "5G"}
VALID_TIME_LEVELS = {"minute", "hour", "day", "month"}

# Reusable SQL tenure band derivation expression
TENURE_BAND_SQL_EXPR = """(
    CASE 
        WHEN c.tenure <= 12 THEN '0-12 months'
        WHEN c.tenure <= 24 THEN '13-24 months'
        WHEN c.tenure <= 48 THEN '25-48 months'
        ELSE '49-72 months'
    END
)"""

# Safe mapping of user-friendly customer attribute names to SQL columns
CUSTOMER_DIMENSION_COLUMN_MAP = {
    "contract": "p.Contract",
    "internet_service": "p.InternetService",
    "payment_method": "p.PaymentMethod",
    "phone_service": "p.PhoneService",
    "multiple_lines": "p.MultipleLines",
    "online_security": "p.OnlineSecurity",
    "online_backup": "p.OnlineBackup",
    "device_protection": "p.DeviceProtection",
    "tech_support": "p.TechSupport",
    "streaming_tv": "p.StreamingTV",
    "streaming_movies": "p.StreamingMovies",
    "paperless_billing": "p.PaperlessBilling",
    "gender": "c.gender",
    "senior_citizen": "c.SeniorCitizen",
    "partner": "c.Partner",
    "dependents": "c.Dependents",
    "churn_flag": "f.churn_flag",
    "tenure_band": TENURE_BAND_SQL_EXPR,
}

# Safe mapping of user-friendly network attribute names to SQL columns
NETWORK_DIMENSION_COLUMN_MAP = {
    "region": "r.region_name",
    "cell_id": "c.cell_id",
    "technology": "tech.technology_name",
    "date": "t.date",
    "hour": "t.hour",
    "minute": "t.minute",
    "day": "t.day",
    "month": "t.month",
    "year": "t.year",
}


def get_default_db_path() -> str:
    """Returns the absolute path to the SQLite warehouse database."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(base_dir, "database", "warehouse.db")


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Establishes and returns a SQLite connection configured with row factory.
    
    Parameters:
        db_path: Optional path to warehouse.db. Uses default if None.
    
    Returns:
        sqlite3.Connection: Connected database instance with row access.
    """
    path = db_path or get_default_db_path()
    if not os.path.exists(path):
        raise FileNotFoundError(f"Database warehouse not found at path: {path}")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def execute_query(
    conn_or_path: Union[sqlite3.Connection, str, None],
    sql: str,
    params: Optional[Union[List[Any], Tuple[Any, ...]]] = None,
) -> List[Dict[str, Any]]:
    """
    Executes a parameterized SQL query safely and returns records as dictionaries.
    
    Parameters:
        conn_or_path: sqlite3.Connection, database file path string, or None (default path).
        sql: Parameterized SQL statement with '?' placeholders.
        params: Tuple or list of bound parameters.
        
    Returns:
        List[Dict[str, Any]]: Query result rows mapped to dictionary objects.
    """
    params = params or ()
    owns_connection = False

    if isinstance(conn_or_path, sqlite3.Connection):
        conn = conn_or_path
    else:
        conn = get_connection(conn_or_path)
        owns_connection = True

    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        if owns_connection:
            conn.close()
