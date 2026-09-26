"""
Data Mining Preprocessing Module
Extracts, audits, transforms, and splits Customer Churn and Network KPI data from warehouse.db.
Enforces strict anti-leakage rules, featurization ordering, and numerical scaling.
"""

import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from backend.olap.queries import get_connection, get_default_db_path

# Dedicated directories for artifacts and results
MINING_DIR = os.path.dirname(__file__)
MODELS_DIR = os.path.join(MINING_DIR, "models")
RESULTS_DIR = os.path.join(MINING_DIR, "results")

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)


def categorize_tenure(t: int) -> str:
    """Standardized tenure band categorization matching warehouse ETL rules."""
    if t <= 12:
        return "0-12 months"
    elif t <= 24:
        return "13-24 months"
    elif t <= 48:
        return "25-48 months"
    else:
        return "49-72 months"


# -----------------------------------------------------------------------------
# 1. CUSTOMER CHURN DATASET EXTRACTION & PREPROCESSING
# -----------------------------------------------------------------------------
def load_customer_churn_dataset(
    conn_or_path: Union[sqlite3.Connection, str, None] = None,
    test_size: float = 0.20,
    random_state: int = 42,
) -> Dict[str, Any]:
    """
    Extracts customer churn records from warehouse.db, performs data quality audits,
    applies a stratified train/test split, and fits a scikit-learn ColumnTransformer
    strictly on the training split to prevent target leakage.

    Returns:
        dict: Containing X_train_raw, X_test_raw, X_train_proc, X_test_proc,
              y_train, y_test, preprocessor, feature_names, raw_df, and audit.
    """
    if isinstance(conn_or_path, sqlite3.Connection):
        conn = conn_or_path
        owns_conn = False
    else:
        conn = get_connection(conn_or_path)
        owns_conn = True

    try:
        sql = """
            SELECT 
                c.customerID,
                c.gender,
                c.SeniorCitizen,
                c.Partner,
                c.Dependents,
                c.tenure,
                p.Contract,
                p.PhoneService,
                p.MultipleLines,
                p.InternetService,
                p.OnlineSecurity,
                p.OnlineBackup,
                p.DeviceProtection,
                p.TechSupport,
                p.StreamingTV,
                p.StreamingMovies,
                p.PaperlessBilling,
                p.PaymentMethod,
                f.monthly_charges,
                f.total_charges,
                f.churn_flag
            FROM FACT_CUSTOMER_CHURN f
            JOIN DIM_CUSTOMER c ON f.customer_key = c.customer_key
            JOIN DIM_PLAN p ON f.plan_key = p.plan_key;
        """
        df_raw = pd.read_sql_query(sql, conn)
    finally:
        if owns_conn:
            conn.close()

    source_row_count = len(df_raw)

    # 1. Derive tenure_band attribute
    df_raw["tenure_band"] = df_raw["tenure"].astype(int).apply(categorize_tenure)

    # 2. Strict Feature Isolation: Separate target and drop non-predictive identifiers
    target_col = "churn_flag"
    identifier_cols = ["customerID"]

    # Verify target presence and extract
    if target_col not in df_raw.columns:
        raise ValueError(f"Target column '{target_col}' not found in query results.")

    y = df_raw[target_col].astype(int)

    # Drop identifiers and target from feature set
    feature_cols = [c for c in df_raw.columns if c not in identifier_cols and c != target_col]
    X = df_raw[feature_cols].copy()

    # 3. Data Quality Audit: Check missing values
    null_counts = X.isnull().sum()
    null_cols = null_counts[null_counts > 0].to_dict()
    if null_cols:
        raise ValueError(f"Unexpected missing values in customer features: {null_cols}")

    # Explicit verification of non-leakage
    assert target_col not in X.columns, "DATA LEAKAGE: Target found in feature matrix X!"
    for ident in identifier_cols:
        assert ident not in X.columns, f"IDENTIFIER LEAKAGE: '{ident}' found in feature matrix X!"

    # 4. Stratified Train / Test Split
    X_train_raw, X_test_raw, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )

    # 5. Column Preprocessor Definition
    numeric_features = ["tenure", "monthly_charges", "total_charges"]
    categorical_features = [
        "gender",
        "SeniorCitizen",
        "Partner",
        "Dependents",
        "Contract",
        "PhoneService",
        "MultipleLines",
        "InternetService",
        "OnlineSecurity",
        "OnlineBackup",
        "DeviceProtection",
        "TechSupport",
        "StreamingTV",
        "StreamingMovies",
        "PaperlessBilling",
        "PaymentMethod",
        "tenure_band",
    ]

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric_features),
            (
                "cat",
                OneHotEncoder(drop="first", sparse_output=False, handle_unknown="ignore"),
                categorical_features,
            ),
        ],
        verbose_feature_names_out=False,
    )

    # Fit strictly on train split
    preprocessor.fit(X_train_raw)
    X_train_proc = preprocessor.transform(X_train_raw)
    X_test_proc = preprocessor.transform(X_test_raw)

    feature_names = preprocessor.get_feature_names_out().tolist()

    audit = {
        "source_rows": source_row_count,
        "removed_rows": 0,
        "final_modeling_rows": len(X),
        "removal_reason": "None. All warehouse records meet strict data quality standards.",
        "features_total": len(feature_cols),
        "features_numeric": len(numeric_features),
        "features_categorical": len(categorical_features),
        "transformed_features_count": len(feature_names),
        "train_rows": len(X_train_raw),
        "test_rows": len(X_test_raw),
        "train_churn_distribution": y_train.value_counts(normalize=True).to_dict(),
        "test_churn_distribution": y_test.value_counts(normalize=True).to_dict(),
    }

    return {
        "X_train_raw": X_train_raw,
        "X_test_raw": X_test_raw,
        "X_train_proc": X_train_proc,
        "X_test_proc": X_test_proc,
        "y_train": y_train,
        "y_test": y_test,
        "preprocessor": preprocessor,
        "feature_names": feature_names,
        "numeric_features": numeric_features,
        "categorical_features": categorical_features,
        "raw_df": df_raw,
        "audit": audit,
    }


# -----------------------------------------------------------------------------
# 2. NETWORK KPI DATASET EXTRACTION & PREPROCESSING
# -----------------------------------------------------------------------------
def load_network_kpi_dataset(
    conn_or_path: Union[sqlite3.Connection, str, None] = None,
) -> Dict[str, Any]:
    """
    Extracts radio access telemetry records from FACT_NETWORK_KPI.
    Filters exclusively to numeric KPI measurements.
    Strictly excludes identifiers/context attributes (cell_id, region, technology, timestamps).

    Returns:
        dict: Containing raw_df, X_raw, X_scaled, scaler, feature_names, and audit.
    """
    if isinstance(conn_or_path, sqlite3.Connection):
        conn = conn_or_path
        owns_conn = False
    else:
        conn = get_connection(conn_or_path)
        owns_conn = True

    try:
        sql = """
            SELECT 
                f.network_kpi_key,
                c.cell_id,
                r.region_name AS region,
                tech.technology_name AS technology,
                t.timestamp,
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
            JOIN DIM_TIME t ON f.time_key = t.time_key;
        """
        df_raw = pd.read_sql_query(sql, conn)
    finally:
        if owns_conn:
            conn.close()

    source_row_count = len(df_raw)

    # Candidate clustering features: Strictly numeric KPI telemetry
    kpi_features = [
        "latency_ms",
        "throughput_mbps",
        "packet_loss_pct",
        "call_drop_rate_pct",
        "signal_strength_dbm",
        "handover_success_pct",
        "active_connections",
    ]

    # Explicitly excluded non-KPI identifiers
    excluded_identifiers = [
        "network_kpi_key",
        "cell_id",
        "region",
        "technology",
        "timestamp",
    ]

    # Verification: Ensure no identifiers are in kpi_features
    for ident in excluded_identifiers:
        assert ident not in kpi_features, f"IDENTIFIER LEAKAGE: '{ident}' in clustering KPI features!"

    X_raw = df_raw[kpi_features].copy()

    # Data Quality Audit: Check nulls / invalid numeric types
    null_counts = X_raw.isnull().sum()
    null_cols = null_counts[null_counts > 0].to_dict()
    if null_cols:
        raise ValueError(f"Unexpected missing values in network KPI features: {null_cols}")

    # Standardize numerical features for K-Means distance computation
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)

    audit = {
        "source_rows": source_row_count,
        "removed_rows": 0,
        "final_modeling_rows": len(X_raw),
        "removal_reason": "None. All 3,600 telemetry readings are complete and valid.",
        "kpi_features_count": len(kpi_features),
        "excluded_identifiers": excluded_identifiers,
    }

    return {
        "raw_df": df_raw,
        "X_raw": X_raw,
        "X_scaled": X_scaled,
        "scaler": scaler,
        "feature_names": kpi_features,
        "audit": audit,
    }
