"""
Data Mining Results Routes
Exposes pre-computed models, evaluations, feature importances, cluster profiles,
and association rules from backend/mining/results without retraining per request.
"""

import csv
import json
import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from backend.api.schemas import ApiResponse
from backend.mining.preprocessing import RESULTS_DIR

router = APIRouter(prefix="/mining", tags=["Data Mining"])


def _load_json_result(filename: str) -> Dict[str, Any]:
    """Helper to load JSON artifact from RESULTS_DIR."""
    filepath = os.path.join(RESULTS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(
            status_code=500,
            detail={"code": "ARTIFACT_MISSING", "message": f"Required data mining artifact '{filename}' not found."},
        )
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_csv_result(filename: str) -> List[Dict[str, Any]]:
    """Helper to load CSV artifact from RESULTS_DIR as list of dicts."""
    filepath = os.path.join(RESULTS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(
            status_code=500,
            detail={"code": "ARTIFACT_MISSING", "message": f"Required data mining artifact '{filename}' not found."},
        )
    rows = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            parsed = {}
            for k, v in r.items():
                # Attempt numeric parse
                try:
                    if "." in v:
                        parsed[k] = float(v)
                    else:
                        parsed[k] = int(v)
                except (ValueError, TypeError):
                    parsed[k] = v
            rows.append(parsed)
    return rows


@router.get("/summary", response_model=ApiResponse[Dict[str, Any]])
def mining_summary():
    """
    Returns an analytical summary across all three data mining pipelines:
    Customer Churn Prediction, Network Degradation Clustering, and Association Rule Mining.
    """
    churn_metrics = _load_json_result("churn_metrics.json")
    cluster_metrics = _load_json_result("clustering_metrics.json")
    rules = _load_csv_result("association_rules.csv")

    summary = {
        "analytical_source": "warehouse_historical_data_mining",
        "simulated": False,
        "customer_churn": {
            "models_trained": list(churn_metrics.get("models", {}).keys()),
            "logistic_regression_roc_auc": churn_metrics.get("models", {}).get("logistic_regression", {}).get("roc_auc"),
            "decision_tree_roc_auc": churn_metrics.get("models", {}).get("decision_tree", {}).get("roc_auc"),
        },
        "network_clustering": {
            "algorithm": "K-Means",
            "k_values_evaluated": cluster_metrics.get("tested_k_values", []),
            "selected_demonstration_k": cluster_metrics.get("selected_k", 3),
        },
        "association_rules": {
            "algorithm": "Apriori Pattern Mining",
            "total_rules_mined": len(rules),
            "target_consequent": "Churn = Yes",
        },
    }
    return ApiResponse(success=True, data=summary)


@router.get("/churn", response_model=ApiResponse[Dict[str, Any]])
def get_churn_prediction_results():
    """
    Returns supervised Customer Churn prediction metrics, confusion matrices,
    and ranked explanatory feature importance coefficients.
    """
    metrics = _load_json_result("churn_metrics.json")
    features = _load_csv_result("churn_feature_importance.csv")

    data = {
        "analytical_type": "supervised_classification",
        "target": "churn_flag (0=No Churn, 1=Churn)",
        "simulated": False,
        "evaluation_metrics": metrics.get("models", {}),
        "class_distribution_test": metrics.get("class_distribution_test", {}),
        "trade_off_analysis": metrics.get("trade_off_analysis", ""),
        "feature_importances": features,
    }
    return ApiResponse(success=True, data=data)


@router.get("/clusters", response_model=ApiResponse[Dict[str, Any]])
def get_network_clustering_results():
    """
    Returns unsupervised K-Means network degradation clustering evaluation metrics,
    silhouette analysis across K=2..5, and domain KPI profiles for demonstration K=3.
    """
    metrics = _load_json_result("clustering_metrics.json")
    profiles = _load_csv_result("cluster_profiles.csv")

    data = {
        "analytical_type": "unsupervised_kpi_clustering",
        "simulated": False,
        "k_evaluation": metrics.get("metrics", {}),
        "selected_k": metrics.get("selected_k", 3),
        "selection_rationale": metrics.get("selection_rationale", ""),
        "cluster_profiles": profiles,
    }
    return ApiResponse(success=True, data=data)


@router.get("/association-rules", response_model=ApiResponse[Dict[str, Any]])
def get_association_rules(
    churn_only: bool = Query(True, description="Filter rules where consequent is 'Churn = Yes'"),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0, description="Minimum confidence filter"),
    limit: int = Query(50, ge=1, le=500, description="Maximum rules to return"),
):
    """
    Returns customer service pattern association rules mined using the Apriori algorithm.
    Includes Support, Confidence, and Lift.
    """
    rules = _load_csv_result("association_rules.csv")

    filtered = []
    for r in rules:
        cons = str(r.get("consequent", "")).replace(" ", "")
        if churn_only and cons != "Churn=Yes":
            continue
        conf = float(r.get("confidence", 0.0))
        if conf < min_confidence:
            continue
        filtered.append(r)

    # Sort by lift descending
    filtered.sort(key=lambda x: float(x.get("lift", 0.0)), reverse=True)
    filtered = filtered[:limit]

    data = {
        "analytical_type": "association_rule_mining",
        "algorithm": "Apriori",
        "simulated": False,
        "total_rules_available": len(rules),
        "filtered_rules_count": len(filtered),
        "rules": filtered,
    }
    return ApiResponse(success=True, data=data)
