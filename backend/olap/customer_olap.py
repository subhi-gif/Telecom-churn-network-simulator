"""
Customer OLAP Engine Module
Implements multidimensional analytical operations (Roll-up, Drill-down, Slice, Dice, Summary)
over the Customer Churn Star Schema (FACT_CUSTOMER_CHURN, DIM_CUSTOMER, DIM_PLAN).
Enforces zero cross-fact joins and parameterized query execution.
"""

import sqlite3
from typing import Any, Dict, List, Optional, Union

from backend.olap.queries import (
    CUSTOMER_DIMENSION_COLUMN_MAP,
    TENURE_BAND_SQL_EXPR,
    VALID_CONTRACTS,
    VALID_INTERNET_SERVICES,
    VALID_PAYMENT_METHODS,
    VALID_TENURE_BANDS,
    execute_query,
    get_connection,
)


class CustomerOLAP:
    """
    OLAP Analytical Engine for the Customer Churn Mart.
    Operates strictly on FACT_CUSTOMER_CHURN, DIM_CUSTOMER, and DIM_PLAN.
    """

    def __init__(self, conn_or_path: Union[sqlite3.Connection, str, None] = None):
        """
        Initializes the Customer OLAP engine.

        Parameters:
            conn_or_path: Active sqlite3.Connection, path to warehouse.db, or None for default.
        """
        self.conn_or_path = conn_or_path

    # -------------------------------------------------------------------------
    # 1. CUSTOMER KPI SUMMARY
    # -------------------------------------------------------------------------
    def get_customer_summary(self) -> Dict[str, Any]:
        """
        Returns high-level aggregate KPIs across the entire Customer Churn Mart.

        Calculates:
            - total customers
            - churned customers
            - non-churned customers
            - churn rate (%)
            - average monthly charges ($)
            - average total charges ($)
        """
        sql = """
            SELECT 
                COUNT(*) AS total_customers,
                COALESCE(SUM(f.churn_flag), 0) AS churned_customers,
                COALESCE(SUM(CASE WHEN f.churn_flag = 0 THEN 1 ELSE 0 END), 0) AS non_churned_customers,
                ROUND(COALESCE(AVG(f.churn_flag) * 100.0, 0.0), 2) AS churn_rate_pct,
                ROUND(COALESCE(AVG(f.monthly_charges), 0.0), 2) AS avg_monthly_charges,
                ROUND(COALESCE(AVG(f.total_charges), 0.0), 2) AS avg_total_charges
            FROM FACT_CUSTOMER_CHURN f;
        """
        rows = execute_query(self.conn_or_path, sql)
        result = rows[0] if rows else {
            "total_customers": 0,
            "churned_customers": 0,
            "non_churned_customers": 0,
            "churn_rate_pct": 0.0,
            "avg_monthly_charges": 0.0,
            "avg_total_charges": 0.0,
        }

        return {
            "operation": "customer_summary",
            "status": "success",
            "results": result,
        }

    # -------------------------------------------------------------------------
    # 2. CUSTOMER ROLL-UP (Customer -> Tenure Band)
    # -------------------------------------------------------------------------
    def get_customer_rollup(self, group_by: str = "tenure_band") -> Dict[str, Any]:
        """
        Aggregates individual customer records into analytical tenure bands.

        Supported Groups (ETL standard):
            - 0-12 months
            - 13-24 months
            - 25-48 months
            - 49-72 months

        Calculates per group:
            - customer count
            - churned customer count
            - non-churned customer count
            - churn rate (%)
            - average monthly charges ($)
            - average total charges ($)
        """
        normalized_group = group_by.strip().lower()
        if normalized_group != "tenure_band":
            return {
                "operation": "customer_rollup",
                "group_by": group_by,
                "status": "error",
                "message": f"Unsupported roll-up group: '{group_by}'. Expected 'tenure_band'.",
                "results": [],
            }

        sql = f"""
            SELECT 
                {TENURE_BAND_SQL_EXPR} AS tenure_band,
                COUNT(*) AS customer_count,
                COALESCE(SUM(f.churn_flag), 0) AS churned_customers,
                COALESCE(SUM(CASE WHEN f.churn_flag = 0 THEN 1 ELSE 0 END), 0) AS non_churned_customers,
                ROUND(COALESCE(AVG(f.churn_flag) * 100.0, 0.0), 2) AS churn_rate_pct,
                ROUND(COALESCE(AVG(f.monthly_charges), 0.0), 2) AS avg_monthly_charges,
                ROUND(COALESCE(AVG(f.total_charges), 0.0), 2) AS avg_total_charges
            FROM FACT_CUSTOMER_CHURN f
            JOIN DIM_CUSTOMER c ON f.customer_key = c.customer_key
            GROUP BY tenure_band
            ORDER BY MIN(c.tenure) ASC;
        """
        rows = execute_query(self.conn_or_path, sql)

        return {
            "operation": "customer_rollup",
            "group_by": "tenure_band",
            "status": "success",
            "results": rows,
        }

    # -------------------------------------------------------------------------
    # 3. CUSTOMER DRILL-DOWN (Tenure Band -> Contract)
    # -------------------------------------------------------------------------
    def get_customer_drilldown(self, tenure_band: str = "0-12 months") -> Dict[str, Any]:
        """
        Drills down from a selected tenure band into contract categories.

        Parameters:
            tenure_band (str): The analytical tenure band to expand (e.g., '0-12 months').

        Returns per contract type:
            - contract type
            - customer count
            - churned customers
            - churn rate (%)
            - average monthly charges ($)
        """
        clean_band = str(tenure_band).strip()
        if clean_band not in VALID_TENURE_BANDS:
            return {
                "operation": "customer_drilldown",
                "hierarchy": "tenure_band -> contract",
                "parameters": {"tenure_band": tenure_band},
                "status": "error",
                "message": (
                    f"Invalid tenure band: '{tenure_band}'. "
                    f"Valid bands are: {sorted(list(VALID_TENURE_BANDS))}"
                ),
                "results": [],
            }

        sql = f"""
            SELECT 
                p.Contract AS contract,
                COUNT(*) AS customer_count,
                COALESCE(SUM(f.churn_flag), 0) AS churned_customers,
                ROUND(COALESCE(AVG(f.churn_flag) * 100.0, 0.0), 2) AS churn_rate_pct,
                ROUND(COALESCE(AVG(f.monthly_charges), 0.0), 2) AS avg_monthly_charges
            FROM FACT_CUSTOMER_CHURN f
            JOIN DIM_CUSTOMER c ON f.customer_key = c.customer_key
            JOIN DIM_PLAN p ON f.plan_key = p.plan_key
            WHERE {TENURE_BAND_SQL_EXPR} = ?
            GROUP BY p.Contract
            ORDER BY customer_count DESC;
        """
        rows = execute_query(self.conn_or_path, sql, (clean_band,))

        return {
            "operation": "customer_drilldown",
            "hierarchy": "tenure_band -> contract",
            "parameters": {"tenure_band": clean_band},
            "status": "success",
            "results": rows,
        }

    # -------------------------------------------------------------------------
    # 4. CUSTOMER SLICE (Single Dimension Filter)
    # -------------------------------------------------------------------------
    def get_customer_slice(self, dimension: str, value: Any) -> Dict[str, Any]:
        """
        Slices the customer cube across exactly one dimension value.

        Supported Dimensions:
            - 'contract': 'Month-to-month', 'One year', 'Two year'
            - 'internet_service': 'DSL', 'Fiber optic', 'No'
            - 'payment_method': 'Electronic check', 'Mailed check',
                                'Bank transfer (automatic)', 'Credit card (automatic)'
            - 'tenure_band': '0-12 months', '13-24 months', '25-48 months', '49-72 months'
            - and other valid customer/plan dimensions.

        Returns aggregated churn metrics for the slice.
        """
        dim_norm = dimension.strip().lower().replace(" ", "_").replace("-", "_")
        col_expr = CUSTOMER_DIMENSION_COLUMN_MAP.get(dim_norm)

        if not col_expr:
            return {
                "operation": "customer_slice",
                "filters": {dimension: value},
                "status": "error",
                "message": (
                    f"Unknown or unsupported customer dimension: '{dimension}'. "
                    f"Supported dimensions: {sorted(list(CUSTOMER_DIMENSION_COLUMN_MAP.keys()))}"
                ),
                "results": {},
            }

        # Domain validation for major dimensions
        val_str = str(value).strip() if value is not None else ""
        if dim_norm == "contract" and val_str not in VALID_CONTRACTS:
            return {
                "operation": "customer_slice",
                "filters": {dimension: value},
                "status": "error",
                "message": f"Invalid Contract '{value}'. Valid: {sorted(list(VALID_CONTRACTS))}",
                "results": {},
            }
        elif dim_norm == "internet_service" and val_str not in VALID_INTERNET_SERVICES:
            return {
                "operation": "customer_slice",
                "filters": {dimension: value},
                "status": "error",
                "message": f"Invalid InternetService '{value}'. Valid: {sorted(list(VALID_INTERNET_SERVICES))}",
                "results": {},
            }
        elif dim_norm == "payment_method" and val_str not in VALID_PAYMENT_METHODS:
            return {
                "operation": "customer_slice",
                "filters": {dimension: value},
                "status": "error",
                "message": f"Invalid PaymentMethod '{value}'. Valid: {sorted(list(VALID_PAYMENT_METHODS))}",
                "results": {},
            }
        elif dim_norm == "tenure_band" and val_str not in VALID_TENURE_BANDS:
            return {
                "operation": "customer_slice",
                "filters": {dimension: value},
                "status": "error",
                "message": f"Invalid tenure_band '{value}'. Valid: {sorted(list(VALID_TENURE_BANDS))}",
                "results": {},
            }

        sql = f"""
            SELECT 
                COUNT(*) AS customer_count,
                COALESCE(SUM(f.churn_flag), 0) AS churned_count,
                COALESCE(SUM(CASE WHEN f.churn_flag = 0 THEN 1 ELSE 0 END), 0) AS non_churned_count,
                ROUND(COALESCE(AVG(f.churn_flag) * 100.0, 0.0), 2) AS churn_rate_pct,
                ROUND(COALESCE(AVG(f.monthly_charges), 0.0), 2) AS avg_monthly_charges,
                ROUND(COALESCE(AVG(f.total_charges), 0.0), 2) AS avg_total_charges
            FROM FACT_CUSTOMER_CHURN f
            JOIN DIM_CUSTOMER c ON f.customer_key = c.customer_key
            JOIN DIM_PLAN p ON f.plan_key = p.plan_key
            WHERE {col_expr} = ?;
        """
        rows = execute_query(self.conn_or_path, sql, (val_str,))
        result = rows[0] if rows else {
            "customer_count": 0,
            "churned_count": 0,
            "non_churned_count": 0,
            "churn_rate_pct": 0.0,
            "avg_monthly_charges": 0.0,
            "avg_total_charges": 0.0,
        }

        return {
            "operation": "customer_slice",
            "filters": {dimension: val_str},
            "status": "success",
            "results": result,
        }

    # -------------------------------------------------------------------------
    # 5. CUSTOMER DICE (Multi-Dimension Filter)
    # -------------------------------------------------------------------------
    def get_customer_dice(
        self,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Dices the customer cube across multiple simultaneous dimensions.

        Supported filter parameters:
            - contract (str): 'Month-to-month', 'One year', 'Two year'
            - internet_service (str): 'DSL', 'Fiber optic', 'No'
            - payment_method (str): payment method string
            - tenure_band (str): '0-12 months', '13-24 months', etc.
            - churn_flag (int or str): 1, 0, 'Yes', 'No'
            - gender, partner, dependents, senior_citizen, etc.

        Returns aggregated customer churn metrics for the multi-filtered subcube.
        """
        combined_filters = dict(filters or {})
        combined_filters.update(kwargs)

        # Drop None or empty string filters
        active_filters = {
            k: v for k, v in combined_filters.items() if v is not None and v != ""
        }

        if not active_filters:
            # If no filters supplied, return overall customer summary
            summary = self.get_customer_summary()
            res = summary["results"]
            return {
                "operation": "customer_dice",
                "filters": {},
                "status": "success",
                "results": {
                    "customer_count": res["total_customers"],
                    "churned_count": res["churned_customers"],
                    "non_churned_count": res["non_churned_customers"],
                    "churn_rate_pct": res["churn_rate_pct"],
                    "avg_monthly_charges": res["avg_monthly_charges"],
                    "avg_total_charges": res["avg_total_charges"],
                },
            }

        where_clauses = []
        params = []

        for dim, val in active_filters.items():
            dim_norm = dim.strip().lower().replace(" ", "_").replace("-", "_")
            col_expr = CUSTOMER_DIMENSION_COLUMN_MAP.get(dim_norm)

            if not col_expr:
                return {
                    "operation": "customer_dice",
                    "filters": active_filters,
                    "status": "error",
                    "message": f"Unsupported filter dimension: '{dim}'.",
                    "results": {},
                }

            # Normalize values
            if dim_norm == "churn_flag":
                if str(val).strip().lower() in ("yes", "1", "true"):
                    clean_val = 1
                elif str(val).strip().lower() in ("no", "0", "false"):
                    clean_val = 0
                else:
                    return {
                        "operation": "customer_dice",
                        "filters": active_filters,
                        "status": "error",
                        "message": f"Invalid churn_flag value: '{val}'. Expected 0, 1, 'Yes', or 'No'.",
                        "results": {},
                    }
                where_clauses.append(f"{col_expr} = ?")
                params.append(clean_val)
            elif dim_norm == "contract":
                c_val = str(val).strip()
                if c_val not in VALID_CONTRACTS:
                    return {
                        "operation": "customer_dice",
                        "filters": active_filters,
                        "status": "error",
                        "message": f"Invalid Contract: '{val}'.",
                        "results": {},
                    }
                where_clauses.append(f"{col_expr} = ?")
                params.append(c_val)
            elif dim_norm == "internet_service":
                i_val = str(val).strip()
                if i_val not in VALID_INTERNET_SERVICES:
                    return {
                        "operation": "customer_dice",
                        "filters": active_filters,
                        "status": "error",
                        "message": f"Invalid InternetService: '{val}'.",
                        "results": {},
                    }
                where_clauses.append(f"{col_expr} = ?")
                params.append(i_val)
            elif dim_norm == "payment_method":
                p_val = str(val).strip()
                if p_val not in VALID_PAYMENT_METHODS:
                    return {
                        "operation": "customer_dice",
                        "filters": active_filters,
                        "status": "error",
                        "message": f"Invalid PaymentMethod: '{val}'.",
                        "results": {},
                    }
                where_clauses.append(f"{col_expr} = ?")
                params.append(p_val)
            elif dim_norm == "tenure_band":
                t_val = str(val).strip()
                if t_val not in VALID_TENURE_BANDS:
                    return {
                        "operation": "customer_dice",
                        "filters": active_filters,
                        "status": "error",
                        "message": f"Invalid tenure_band: '{val}'.",
                        "results": {},
                    }
                where_clauses.append(f"{col_expr} = ?")
                params.append(t_val)
            else:
                where_clauses.append(f"{col_expr} = ?")
                params.append(val)

        where_sql = " AND ".join(where_clauses)
        sql = f"""
            SELECT 
                COUNT(*) AS customer_count,
                COALESCE(SUM(f.churn_flag), 0) AS churned_count,
                COALESCE(SUM(CASE WHEN f.churn_flag = 0 THEN 1 ELSE 0 END), 0) AS non_churned_count,
                ROUND(COALESCE(AVG(f.churn_flag) * 100.0, 0.0), 2) AS churn_rate_pct,
                ROUND(COALESCE(AVG(f.monthly_charges), 0.0), 2) AS avg_monthly_charges,
                ROUND(COALESCE(AVG(f.total_charges), 0.0), 2) AS avg_total_charges
            FROM FACT_CUSTOMER_CHURN f
            JOIN DIM_CUSTOMER c ON f.customer_key = c.customer_key
            JOIN DIM_PLAN p ON f.plan_key = p.plan_key
            WHERE {where_sql};
        """
        rows = execute_query(self.conn_or_path, sql, params)
        result = rows[0] if rows else {
            "customer_count": 0,
            "churned_count": 0,
            "non_churned_count": 0,
            "churn_rate_pct": 0.0,
            "avg_monthly_charges": 0.0,
            "avg_total_charges": 0.0,
        }

        return {
            "operation": "customer_dice",
            "filters": active_filters,
            "status": "success",
            "results": result,
        }


# -----------------------------------------------------------------------------
# CONVENIENCE PROCEDURAL WRAPPERS
# -----------------------------------------------------------------------------
def get_customer_summary(conn_or_path=None) -> Dict[str, Any]:
    return CustomerOLAP(conn_or_path).get_customer_summary()


def get_customer_rollup(group_by="tenure_band", conn_or_path=None) -> Dict[str, Any]:
    return CustomerOLAP(conn_or_path).get_customer_rollup(group_by=group_by)


def get_customer_drilldown(tenure_band="0-12 months", conn_or_path=None) -> Dict[str, Any]:
    return CustomerOLAP(conn_or_path).get_customer_drilldown(tenure_band=tenure_band)


def get_customer_slice(dimension: str, value: Any, conn_or_path=None) -> Dict[str, Any]:
    return CustomerOLAP(conn_or_path).get_customer_slice(dimension=dimension, value=value)


def get_customer_dice(filters=None, conn_or_path=None, **kwargs) -> Dict[str, Any]:
    return CustomerOLAP(conn_or_path).get_customer_dice(filters=filters, **kwargs)
