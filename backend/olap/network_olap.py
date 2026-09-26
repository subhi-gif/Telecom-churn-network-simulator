"""
Network OLAP Engine Module
Implements multidimensional analytical operations (Roll-up, Drill-down, Slice, Dice,
High-Call-Drop Analysis, and Summary) over the Network Performance Star Schema
(FACT_NETWORK_KPI, DIM_CELL, DIM_REGION, DIM_NETWORK_TECH, DIM_TIME).
Enforces zero cross-fact joins and parameterized query execution.
"""

import sqlite3
from typing import Any, Dict, List, Optional, Union

from backend.olap.queries import (
    NETWORK_DIMENSION_COLUMN_MAP,
    VALID_REGIONS,
    VALID_TECHNOLOGIES,
    VALID_TIME_LEVELS,
    execute_query,
    get_connection,
)


class NetworkOLAP:
    """
    OLAP Analytical Engine for the Network Performance Mart.
    Operates strictly on FACT_NETWORK_KPI, DIM_CELL, DIM_REGION, DIM_NETWORK_TECH, DIM_TIME.
    """

    def __init__(self, conn_or_path: Union[sqlite3.Connection, str, None] = None):
        """
        Initializes the Network OLAP engine.

        Parameters:
            conn_or_path: Active sqlite3.Connection, path to warehouse.db, or None for default.
        """
        self.conn_or_path = conn_or_path

    # -------------------------------------------------------------------------
    # 1. NETWORK KPI SUMMARY
    # -------------------------------------------------------------------------
    def get_network_summary(self) -> Dict[str, Any]:
        """
        Returns high-level aggregate KPIs across the entire Network Performance Mart.

        Calculates:
            - total observations
            - number of cells
            - number of regions
            - number of technologies
            - average latency (ms)
            - average throughput (Mbps)
            - average packet loss (%)
            - average call drop rate (%)
            - average signal strength (dBm)
            - average handover success (%)
            - average active connections
        """
        sql = """
            SELECT 
                COUNT(*) AS total_observations,
                COUNT(DISTINCT f.cell_key) AS number_of_cells,
                COUNT(DISTINCT f.region_key) AS number_of_regions,
                COUNT(DISTINCT f.technology_key) AS number_of_technologies,
                ROUND(COALESCE(AVG(f.latency_ms), 0.0), 2) AS avg_latency_ms,
                ROUND(COALESCE(AVG(f.throughput_mbps), 0.0), 2) AS avg_throughput_mbps,
                ROUND(COALESCE(AVG(f.packet_loss_pct), 0.0), 2) AS avg_packet_loss_pct,
                ROUND(COALESCE(AVG(f.call_drop_rate_pct), 0.0), 2) AS avg_call_drop_rate_pct,
                ROUND(COALESCE(AVG(f.signal_strength_dbm), 0.0), 2) AS avg_signal_strength_dbm,
                ROUND(COALESCE(AVG(f.handover_success_pct), 0.0), 2) AS avg_handover_success_pct,
                ROUND(COALESCE(AVG(f.active_connections), 0.0), 2) AS avg_active_connections
            FROM FACT_NETWORK_KPI f;
        """
        rows = execute_query(self.conn_or_path, sql)
        result = rows[0] if rows else {
            "total_observations": 0,
            "number_of_cells": 0,
            "number_of_regions": 0,
            "number_of_technologies": 0,
            "avg_latency_ms": 0.0,
            "avg_throughput_mbps": 0.0,
            "avg_packet_loss_pct": 0.0,
            "avg_call_drop_rate_pct": 0.0,
            "avg_signal_strength_dbm": 0.0,
            "avg_handover_success_pct": 0.0,
            "avg_active_connections": 0.0,
        }

        return {
            "operation": "network_summary",
            "status": "success",
            "results": result,
        }

    # -------------------------------------------------------------------------
    # 2. NETWORK ROLL-UP (Time: Minute -> Hour -> Day -> Month)
    # -------------------------------------------------------------------------
    def get_network_rollup(self, level: str = "minute") -> Dict[str, Any]:
        """
        Performs time-based roll-up aggregation across telemetry timestamps.

        Hierarchy levels:
            - 'minute': 1-minute telemetry intervals (t.timestamp)
            - 'hour': hourly buckets (t.date + t.hour)
            - 'day': daily buckets (t.date)
            - 'month': monthly buckets (t.year + t.month)

        Calculates for each time bucket:
            - time_bucket
            - observation_count
            - average latency (ms)
            - average throughput (Mbps)
            - average packet loss (%)
            - average call drop rate (%)
            - average signal strength (dBm)
            - average handover success (%)
            - average active connections
        """
        lvl = level.strip().lower()
        if lvl not in VALID_TIME_LEVELS:
            return {
                "operation": "network_rollup",
                "level": level,
                "status": "error",
                "message": (
                    f"Invalid time roll-up level: '{level}'. "
                    f"Supported levels: {sorted(list(VALID_TIME_LEVELS))}"
                ),
                "results": [],
            }

        if lvl == "minute":
            select_bucket = "t.timestamp AS time_bucket"
            group_expr = "t.timestamp"
        elif lvl == "hour":
            select_bucket = "(t.date || ' ' || printf('%02d:00:00', t.hour)) AS time_bucket"
            group_expr = "t.date, t.hour"
        elif lvl == "day":
            select_bucket = "t.date AS time_bucket"
            group_expr = "t.date"
        else:  # month
            select_bucket = "printf('%04d-%02d', t.year, t.month) AS time_bucket"
            group_expr = "t.year, t.month"

        sql = f"""
            SELECT 
                {select_bucket},
                COUNT(*) AS observation_count,
                ROUND(COALESCE(AVG(f.latency_ms), 0.0), 2) AS avg_latency_ms,
                ROUND(COALESCE(AVG(f.throughput_mbps), 0.0), 2) AS avg_throughput_mbps,
                ROUND(COALESCE(AVG(f.packet_loss_pct), 0.0), 2) AS avg_packet_loss_pct,
                ROUND(COALESCE(AVG(f.call_drop_rate_pct), 0.0), 2) AS avg_call_drop_rate_pct,
                ROUND(COALESCE(AVG(f.signal_strength_dbm), 0.0), 2) AS avg_signal_strength_dbm,
                ROUND(COALESCE(AVG(f.handover_success_pct), 0.0), 2) AS avg_handover_success_pct,
                ROUND(COALESCE(AVG(f.active_connections), 0.0), 2) AS avg_active_connections
            FROM FACT_NETWORK_KPI f
            JOIN DIM_TIME t ON f.time_key = t.time_key
            GROUP BY {group_expr}
            ORDER BY MIN(t.timestamp) ASC;
        """
        rows = execute_query(self.conn_or_path, sql)

        return {
            "operation": "network_rollup",
            "level": lvl,
            "status": "success",
            "results": rows,
        }

    # -------------------------------------------------------------------------
    # 3. NETWORK DRILL-DOWN (Region -> Cell -> Time)
    # -------------------------------------------------------------------------
    def get_network_drilldown(
        self,
        region: str,
        cell_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Drills down along the geographical and topological hierarchy: Region -> Cell -> Time.

        Parameters:
            region (str): Required region filter (e.g. 'North', 'Central', 'East', 'South', 'West').
            cell_id (str, optional): Optional cell filter to drill down directly to the time level.

        Returns:
            - region
            - cell_id
            - technology
            - timestamp / time grouping
            - average latency
            - average throughput
            - average packet loss
            - average call drop rate
            - average signal strength
            - average handover success
            - average active connections
        """
        clean_reg = str(region).strip()
        if clean_reg not in VALID_REGIONS:
            return {
                "operation": "network_drilldown",
                "hierarchy": "region -> cell -> time",
                "parameters": {"region": region, "cell_id": cell_id},
                "status": "error",
                "message": (
                    f"Invalid region: '{region}'. "
                    f"Valid regions are: {sorted(list(VALID_REGIONS))}"
                ),
                "results": [],
            }

        params: List[Any] = [clean_reg]

        if cell_id is not None and str(cell_id).strip():
            clean_cell = str(cell_id).strip()
            params.append(clean_cell)

            # Drill down to Time level for this specific cell
            sql = """
                SELECT 
                    r.region_name AS region,
                    c.cell_id AS cell_id,
                    tech.technology_name AS technology,
                    t.timestamp AS time_grouping,
                    ROUND(COALESCE(AVG(f.latency_ms), 0.0), 2) AS avg_latency_ms,
                    ROUND(COALESCE(AVG(f.throughput_mbps), 0.0), 2) AS avg_throughput_mbps,
                    ROUND(COALESCE(AVG(f.packet_loss_pct), 0.0), 2) AS avg_packet_loss_pct,
                    ROUND(COALESCE(AVG(f.call_drop_rate_pct), 0.0), 2) AS avg_call_drop_rate_pct,
                    ROUND(COALESCE(AVG(f.signal_strength_dbm), 0.0), 2) AS avg_signal_strength_dbm,
                    ROUND(COALESCE(AVG(f.handover_success_pct), 0.0), 2) AS avg_handover_success_pct,
                    ROUND(COALESCE(AVG(f.active_connections), 0.0), 2) AS avg_active_connections
                FROM FACT_NETWORK_KPI f
                JOIN DIM_CELL c ON f.cell_key = c.cell_key
                JOIN DIM_REGION r ON f.region_key = r.region_key
                JOIN DIM_NETWORK_TECH tech ON f.technology_key = tech.technology_key
                JOIN DIM_TIME t ON f.time_key = t.time_key
                WHERE r.region_name = ? AND c.cell_id = ?
                GROUP BY r.region_name, c.cell_id, tech.technology_name, t.timestamp
                ORDER BY t.timestamp ASC;
            """
        else:
            # Drill down to Cell level for the selected region
            sql = """
                SELECT 
                    r.region_name AS region,
                    c.cell_id AS cell_id,
                    tech.technology_name AS technology,
                    '2026-08-03 14:00:00 - 14:29:00 (All)' AS time_grouping,
                    ROUND(COALESCE(AVG(f.latency_ms), 0.0), 2) AS avg_latency_ms,
                    ROUND(COALESCE(AVG(f.throughput_mbps), 0.0), 2) AS avg_throughput_mbps,
                    ROUND(COALESCE(AVG(f.packet_loss_pct), 0.0), 2) AS avg_packet_loss_pct,
                    ROUND(COALESCE(AVG(f.call_drop_rate_pct), 0.0), 2) AS avg_call_drop_rate_pct,
                    ROUND(COALESCE(AVG(f.signal_strength_dbm), 0.0), 2) AS avg_signal_strength_dbm,
                    ROUND(COALESCE(AVG(f.handover_success_pct), 0.0), 2) AS avg_handover_success_pct,
                    ROUND(COALESCE(AVG(f.active_connections), 0.0), 2) AS avg_active_connections
                FROM FACT_NETWORK_KPI f
                JOIN DIM_CELL c ON f.cell_key = c.cell_key
                JOIN DIM_REGION r ON f.region_key = r.region_key
                JOIN DIM_NETWORK_TECH tech ON f.technology_key = tech.technology_key
                WHERE r.region_name = ?
                GROUP BY r.region_name, c.cell_id, tech.technology_name
                ORDER BY c.cell_id ASC;
            """

        rows = execute_query(self.conn_or_path, sql, params)

        return {
            "operation": "network_drilldown",
            "hierarchy": "region -> cell -> time",
            "parameters": {"region": clean_reg, "cell_id": cell_id},
            "status": "success",
            "results": rows,
        }

    # -------------------------------------------------------------------------
    # 4. NETWORK SLICE (Single Dimension Filter)
    # -------------------------------------------------------------------------
    def get_network_slice(self, dimension: str, value: Any) -> Dict[str, Any]:
        """
        Slices the network cube across exactly one dimension value.

        Supported Dimensions:
            - 'technology': 'LTE', '5G'
            - 'region': 'Central', 'East', 'North', 'South', 'West'
            - 'cell_id': cell identifier string (e.g., 'Cell_0001')

        Returns:
            - observation count
            - average latency
            - average throughput
            - average packet loss
            - average call drop rate
            - average signal strength
            - average handover success
            - average active connections
        """
        dim_norm = dimension.strip().lower().replace(" ", "_").replace("-", "_")
        col_expr = NETWORK_DIMENSION_COLUMN_MAP.get(dim_norm)

        if not col_expr:
            return {
                "operation": "network_slice",
                "filters": {dimension: value},
                "status": "error",
                "message": (
                    f"Unsupported network slice dimension: '{dimension}'. "
                    f"Supported dimensions: {sorted(list(NETWORK_DIMENSION_COLUMN_MAP.keys()))}"
                ),
                "results": {},
            }

        val_str = str(value).strip() if value is not None else ""
        if dim_norm == "technology" and val_str not in VALID_TECHNOLOGIES:
            return {
                "operation": "network_slice",
                "filters": {dimension: value},
                "status": "error",
                "message": f"Invalid technology: '{value}'. Valid: {sorted(list(VALID_TECHNOLOGIES))}",
                "results": {},
            }
        elif dim_norm == "region" and val_str not in VALID_REGIONS:
            return {
                "operation": "network_slice",
                "filters": {dimension: value},
                "status": "error",
                "message": f"Invalid region: '{value}'. Valid: {sorted(list(VALID_REGIONS))}",
                "results": {},
            }

        sql = f"""
            SELECT 
                COUNT(*) AS observation_count,
                ROUND(COALESCE(AVG(f.latency_ms), 0.0), 2) AS avg_latency_ms,
                ROUND(COALESCE(AVG(f.throughput_mbps), 0.0), 2) AS avg_throughput_mbps,
                ROUND(COALESCE(AVG(f.packet_loss_pct), 0.0), 2) AS avg_packet_loss_pct,
                ROUND(COALESCE(AVG(f.call_drop_rate_pct), 0.0), 2) AS avg_call_drop_rate_pct,
                ROUND(COALESCE(AVG(f.signal_strength_dbm), 0.0), 2) AS avg_signal_strength_dbm,
                ROUND(COALESCE(AVG(f.handover_success_pct), 0.0), 2) AS avg_handover_success_pct,
                ROUND(COALESCE(AVG(f.active_connections), 0.0), 2) AS avg_active_connections
            FROM FACT_NETWORK_KPI f
            JOIN DIM_CELL c ON f.cell_key = c.cell_key
            JOIN DIM_REGION r ON f.region_key = r.region_key
            JOIN DIM_NETWORK_TECH tech ON f.technology_key = tech.technology_key
            JOIN DIM_TIME t ON f.time_key = t.time_key
            WHERE {col_expr} = ?;
        """
        rows = execute_query(self.conn_or_path, sql, (val_str,))
        result = rows[0] if rows else {
            "observation_count": 0,
            "avg_latency_ms": 0.0,
            "avg_throughput_mbps": 0.0,
            "avg_packet_loss_pct": 0.0,
            "avg_call_drop_rate_pct": 0.0,
            "avg_signal_strength_dbm": 0.0,
            "avg_handover_success_pct": 0.0,
            "avg_active_connections": 0.0,
        }

        return {
            "operation": "network_slice",
            "filters": {dimension: val_str},
            "status": "success",
            "results": result,
        }

    # -------------------------------------------------------------------------
    # 5. NETWORK DICE (Multi-Dimension Filter & Thresholds)
    # -------------------------------------------------------------------------
    def get_network_dice(
        self,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Dices the network cube across multiple simultaneous dimensions and thresholds.

        Supported filter parameters:
            - region (str): 'Central', 'East', 'North', 'South', 'West'
            - technology (str): 'LTE', '5G'
            - cell_id (str): specific cell id
            - call_drop_rate_gt (float): call drop rate threshold lower bound
            - call_drop_rate_lt (float): call drop rate threshold upper bound
            - latency_gt (float): latency threshold lower bound
            - latency_lt (float): latency threshold upper bound
            - throughput_gt (float): throughput threshold lower bound
            - min_active_connections (int): active connections lower bound

        Returns aggregated network KPIs.
        """
        combined_filters = dict(filters or {})
        combined_filters.update(kwargs)

        active_filters = {
            k: v for k, v in combined_filters.items() if v is not None and v != ""
        }

        if not active_filters:
            summary = self.get_network_summary()
            res = summary["results"]
            return {
                "operation": "network_dice",
                "filters": {},
                "status": "success",
                "results": {
                    "observation_count": res["total_observations"],
                    "avg_latency_ms": res["avg_latency_ms"],
                    "avg_throughput_mbps": res["avg_throughput_mbps"],
                    "avg_packet_loss_pct": res["avg_packet_loss_pct"],
                    "avg_call_drop_rate_pct": res["avg_call_drop_rate_pct"],
                    "avg_signal_strength_dbm": res["avg_signal_strength_dbm"],
                    "avg_handover_success_pct": res["avg_handover_success_pct"],
                    "avg_active_connections": res["avg_active_connections"],
                },
            }

        where_clauses = []
        params: List[Any] = []

        for dim, val in active_filters.items():
            dim_norm = dim.strip().lower().replace(" ", "_").replace("-", "_")

            if dim_norm == "region":
                r_val = str(val).strip()
                if r_val not in VALID_REGIONS:
                    return {
                        "operation": "network_dice",
                        "filters": active_filters,
                        "status": "error",
                        "message": f"Invalid region: '{val}'.",
                        "results": {},
                    }
                where_clauses.append("r.region_name = ?")
                params.append(r_val)
            elif dim_norm == "technology":
                t_val = str(val).strip()
                if t_val not in VALID_TECHNOLOGIES:
                    return {
                        "operation": "network_dice",
                        "filters": active_filters,
                        "status": "error",
                        "message": f"Invalid technology: '{val}'.",
                        "results": {},
                    }
                where_clauses.append("tech.technology_name = ?")
                params.append(t_val)
            elif dim_norm == "cell_id":
                where_clauses.append("c.cell_id = ?")
                params.append(str(val).strip())
            elif dim_norm in ("call_drop_rate_gt", "call_drop_rate_pct_gt"):
                try:
                    num = float(val)
                except (ValueError, TypeError):
                    return {
                        "operation": "network_dice",
                        "filters": active_filters,
                        "status": "error",
                        "message": f"Invalid numeric threshold for '{dim}': {val}",
                        "results": {},
                    }
                where_clauses.append("f.call_drop_rate_pct > ?")
                params.append(num)
            elif dim_norm in ("call_drop_rate_lt", "call_drop_rate_pct_lt"):
                try:
                    num = float(val)
                except (ValueError, TypeError):
                    return {
                        "operation": "network_dice",
                        "filters": active_filters,
                        "status": "error",
                        "message": f"Invalid numeric threshold for '{dim}': {val}",
                        "results": {},
                    }
                where_clauses.append("f.call_drop_rate_pct < ?")
                params.append(num)
            elif dim_norm == "latency_gt":
                where_clauses.append("f.latency_ms > ?")
                params.append(float(val))
            elif dim_norm == "latency_lt":
                where_clauses.append("f.latency_ms < ?")
                params.append(float(val))
            elif dim_norm == "throughput_gt":
                where_clauses.append("f.throughput_mbps > ?")
                params.append(float(val))
            elif dim_norm in ("min_active_connections", "active_connections_gt"):
                where_clauses.append("f.active_connections >= ?")
                params.append(int(val))
            else:
                return {
                    "operation": "network_dice",
                    "filters": active_filters,
                    "status": "error",
                    "message": f"Unsupported network filter parameter: '{dim}'.",
                    "results": {},
                }

        where_sql = " AND ".join(where_clauses)
        sql = f"""
            SELECT 
                COUNT(*) AS observation_count,
                ROUND(COALESCE(AVG(f.latency_ms), 0.0), 2) AS avg_latency_ms,
                ROUND(COALESCE(AVG(f.throughput_mbps), 0.0), 2) AS avg_throughput_mbps,
                ROUND(COALESCE(AVG(f.packet_loss_pct), 0.0), 2) AS avg_packet_loss_pct,
                ROUND(COALESCE(AVG(f.call_drop_rate_pct), 0.0), 2) AS avg_call_drop_rate_pct,
                ROUND(COALESCE(AVG(f.signal_strength_dbm), 0.0), 2) AS avg_signal_strength_dbm,
                ROUND(COALESCE(AVG(f.handover_success_pct), 0.0), 2) AS avg_handover_success_pct,
                ROUND(COALESCE(AVG(f.active_connections), 0.0), 2) AS avg_active_connections
            FROM FACT_NETWORK_KPI f
            JOIN DIM_CELL c ON f.cell_key = c.cell_key
            JOIN DIM_REGION r ON f.region_key = r.region_key
            JOIN DIM_NETWORK_TECH tech ON f.technology_key = tech.technology_key
            JOIN DIM_TIME t ON f.time_key = t.time_key
            WHERE {where_sql};
        """
        rows = execute_query(self.conn_or_path, sql, params)
        result = rows[0] if rows else {
            "observation_count": 0,
            "avg_latency_ms": 0.0,
            "avg_throughput_mbps": 0.0,
            "avg_packet_loss_pct": 0.0,
            "avg_call_drop_rate_pct": 0.0,
            "avg_signal_strength_dbm": 0.0,
            "avg_handover_success_pct": 0.0,
            "avg_active_connections": 0.0,
        }

        return {
            "operation": "network_dice",
            "filters": active_filters,
            "status": "success",
            "results": result,
        }

    # -------------------------------------------------------------------------
    # 6. HIGH-CALL-DROP ANALYSIS
    # -------------------------------------------------------------------------
    def get_high_call_drop_cells(self, threshold: float = 2.0) -> Dict[str, Any]:
        """
        Identifies network cells with severe call drop rates exceeding a configurable threshold.

        Parameters:
            threshold (float): Call drop rate percentage cutoff (default: 2.0%).

        Returns grouped by:
            - region
            - cell_id
            - technology

        Metrics returned:
            - observation count
            - average call drop rate (%)
            - average latency (ms)
            - average throughput (Mbps)
            - average active connections
        """
        try:
            thresh_val = float(threshold)
            if thresh_val < 0.0 or thresh_val > 100.0:
                raise ValueError("Threshold must be between 0.0 and 100.0")
        except (ValueError, TypeError):
            return {
                "operation": "high_call_drop_analysis",
                "threshold_pct": threshold,
                "status": "error",
                "message": f"Invalid threshold value: '{threshold}'. Must be numeric (0-100).",
                "results": [],
            }

        sql = """
            SELECT 
                r.region_name AS region,
                c.cell_id AS cell_id,
                tech.technology_name AS technology,
                COUNT(*) AS observation_count,
                ROUND(COALESCE(AVG(f.call_drop_rate_pct), 0.0), 2) AS avg_call_drop_rate_pct,
                ROUND(COALESCE(AVG(f.latency_ms), 0.0), 2) AS avg_latency_ms,
                ROUND(COALESCE(AVG(f.throughput_mbps), 0.0), 2) AS avg_throughput_mbps,
                ROUND(COALESCE(AVG(f.active_connections), 0.0), 2) AS avg_active_connections
            FROM FACT_NETWORK_KPI f
            JOIN DIM_CELL c ON f.cell_key = c.cell_key
            JOIN DIM_REGION r ON f.region_key = r.region_key
            JOIN DIM_NETWORK_TECH tech ON f.technology_key = tech.technology_key
            WHERE f.call_drop_rate_pct > ?
            GROUP BY r.region_name, c.cell_id, tech.technology_name
            ORDER BY avg_call_drop_rate_pct DESC, observation_count DESC;
        """
        rows = execute_query(self.conn_or_path, sql, (thresh_val,))

        return {
            "operation": "high_call_drop_analysis",
            "threshold_pct": thresh_val,
            "status": "success",
            "results": rows,
        }


# -----------------------------------------------------------------------------
# CONVENIENCE PROCEDURAL WRAPPERS
# -----------------------------------------------------------------------------
def get_network_summary(conn_or_path=None) -> Dict[str, Any]:
    return NetworkOLAP(conn_or_path).get_network_summary()


def get_network_rollup(level="minute", conn_or_path=None) -> Dict[str, Any]:
    return NetworkOLAP(conn_or_path).get_network_rollup(level=level)


def get_network_drilldown(region: str, cell_id=None, conn_or_path=None) -> Dict[str, Any]:
    return NetworkOLAP(conn_or_path).get_network_drilldown(region=region, cell_id=cell_id)


def get_network_slice(dimension: str, value: Any, conn_or_path=None) -> Dict[str, Any]:
    return NetworkOLAP(conn_or_path).get_network_slice(dimension=dimension, value=value)


def get_network_dice(filters=None, conn_or_path=None, **kwargs) -> Dict[str, Any]:
    return NetworkOLAP(conn_or_path).get_network_dice(filters=filters, **kwargs)


def get_high_call_drop_cells(threshold=2.0, conn_or_path=None) -> Dict[str, Any]:
    return NetworkOLAP(conn_or_path).get_high_call_drop_cells(threshold=threshold)
