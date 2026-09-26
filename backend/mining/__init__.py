"""
Telecom Data Mining Package
Provides supervised churn prediction, unsupervised network KPI clustering,
and customer service association pattern mining.
"""

from backend.mining.association_rules import (
    CustomerAssociationMiner,
    run_association_mining_pipeline,
)
from backend.mining.churn_model import (
    CustomerChurnPipeline,
    run_churn_pipeline,
)
from backend.mining.network_clustering import (
    NetworkClusteringPipeline,
    run_network_clustering_pipeline,
)
from backend.mining.preprocessing import (
    MODELS_DIR,
    RESULTS_DIR,
    load_customer_churn_dataset,
    load_network_kpi_dataset,
)

__all__ = [
    # Customer Churn Modeling
    "CustomerChurnPipeline",
    "run_churn_pipeline",
    # Network Clustering
    "NetworkClusteringPipeline",
    "run_network_clustering_pipeline",
    # Association Rule Mining
    "CustomerAssociationMiner",
    "run_association_mining_pipeline",
    # Preprocessing & Data Loaders
    "load_customer_churn_dataset",
    "load_network_kpi_dataset",
    "MODELS_DIR",
    "RESULTS_DIR",
]
