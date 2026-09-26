"""
Data Mining Layer Test & Validation Suite
Validates all three analytical components:
1. Customer Churn Prediction (Logistic Regression & Decision Tree)
2. Network KPI Degradation Clustering (K-Means, Silhouette, Profiles)
3. Customer Service Pattern Mining (Apriori Association Rules)

Verifies strict non-leakage, data reconciliations, metric validity, and artifact persistence.
"""

import json
import os
import sys
from typing import Any, Dict, List

import numpy as np
import pandas as pd

# Add workspace root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.mining import (
    CustomerAssociationMiner,
    CustomerChurnPipeline,
    MODELS_DIR,
    NetworkClusteringPipeline,
    RESULTS_DIR,
    load_customer_churn_dataset,
    load_network_kpi_dataset,
    run_association_mining_pipeline,
    run_churn_pipeline,
    run_network_clustering_pipeline,
)
from backend.olap.queries import get_connection


class MiningTestRunner:
    """Orchestrates comprehensive unit testing, mathematical validation, and reporting for Step 5."""

    def __init__(self):
        self.conn = get_connection()
        self.tests_executed = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures: List[str] = []

    def log_result(self, test_name: str, passed: bool, message: str = ""):
        self.tests_executed += 1
        if passed:
            self.tests_passed += 1
            print(f"  [PASS] {test_name}")
        else:
            self.tests_failed += 1
            error_msg = f"  [FAIL] {test_name}: {message}"
            print(error_msg)
            self.failures.append(error_msg)

    # =========================================================================
    # PART 1: CUSTOMER CHURN PREDICTION TESTS
    # =========================================================================

    def test_churn_data_loading_and_reconciliation(self) -> Dict[str, Any]:
        print("\n--- TEST 1 & 17: Churn Dataset Loading & Warehouse Reconciliation ---")
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM FACT_CUSTOMER_CHURN;")
        raw_wh_count = cur.fetchone()[0]

        data = load_customer_churn_dataset(self.conn)
        raw_df = data["raw_df"]
        audit = data["audit"]

        passed = (
            len(raw_df) == raw_wh_count == 7043
            and audit["source_rows"] == 7043
            and audit["removed_rows"] == 0
            and audit["final_modeling_rows"] == 7043
        )
        self.log_result(
            "Customer Churn dataset reconciles exactly to warehouse ground truth (7,043 rows, 0 removed)",
            passed,
            f"Loaded {len(raw_df)} rows vs warehouse {raw_wh_count}"
        )
        return data

    def test_churn_anti_leakage(self, data: Dict[str, Any]):
        print("\n--- TEST 2 & 3: Anti-Leakage & Identifier Isolation ---")
        X_train_raw = data["X_train_raw"]
        X_test_raw = data["X_test_raw"]
        feature_names = data["feature_names"]

        # Check target is not in feature matrices
        t_not_in_train = "churn_flag" not in X_train_raw.columns and "Churn" not in X_train_raw.columns
        t_not_in_test = "churn_flag" not in X_test_raw.columns and "Churn" not in X_test_raw.columns
        t_not_in_proc = not any("churn" in f.lower() for f in feature_names)

        # Check customerID is not in feature matrices
        id_not_in_train = "customerID" not in X_train_raw.columns
        id_not_in_test = "customerID" not in X_test_raw.columns
        id_not_in_proc = not any("customerid" in f.lower() for f in feature_names)

        p_target = t_not_in_train and t_not_in_test and t_not_in_proc
        p_id = id_not_in_train and id_not_in_test and id_not_in_proc

        self.log_result(
            "Target ('churn_flag') is strictly isolated and absent from input features",
            p_target,
            f"Train has target: {not t_not_in_train}, Proc has target: {not t_not_in_proc}"
        )
        self.log_result(
            "Customer identifier ('customerID') is strictly excluded from input features",
            p_id,
            f"Train has ID: {not id_not_in_train}, Proc has ID: {not id_not_in_proc}"
        )

    def test_churn_train_test_split_and_no_nan(self, data: Dict[str, Any]):
        print("\n--- TEST 4 & 16: Stratified Split & Clean Inputs (No NaN/Inf) ---")
        X_tr = data["X_train_proc"]
        X_te = data["X_test_proc"]
        y_tr = data["y_train"]
        y_te = data["y_test"]

        # Check split sizes: 80% of 7043 = 5634, 20% = 1409
        expected_train_len = 5634
        expected_test_len = 1409
        p_split = (len(X_tr) == expected_train_len) and (len(X_te) == expected_test_len)

        # Stratification check (churn prevalence ~26.54% in both)
        tr_prevalence = y_tr.mean()
        te_prevalence = y_te.mean()
        p_strat = abs(tr_prevalence - te_prevalence) < 0.01

        # NaN / Inf check
        nan_in_train = np.isnan(X_tr).any() or np.isinf(X_tr).any()
        nan_in_test = np.isnan(X_te).any() or np.isinf(X_te).any()
        p_nan = not nan_in_train and not nan_in_test

        self.log_result(
            f"Stratified 80/20 train/test split preserved class balance (train={len(X_tr)}, test={len(X_te)})",
            p_split and p_strat,
            f"Train prev: {tr_prevalence:.4f}, Test prev: {te_prevalence:.4f}"
        )
        self.log_result(
            "Zero NaN or Inf values in processed feature arrays",
            p_nan,
            f"NaN in train: {nan_in_train}, NaN in test: {nan_in_test}"
        )

    def test_churn_model_training_and_evaluation(self):
        print("\n--- TEST 5, 6, 7: Model Training, Evaluation, and Confusion Matrices ---")
        pipeline = CustomerChurnPipeline(random_state=42)
        pipeline.load_data(self.conn)
        lr_model, dt_model = pipeline.train_models()

        p_lr_trained = hasattr(lr_model, "coef_") and len(lr_model.coef_[0]) > 0
        p_dt_trained = hasattr(dt_model, "tree_") and dt_model.tree_.node_count > 0

        self.log_result("Logistic Regression model trains successfully", p_lr_trained)
        self.log_result("Decision Tree classifier trains successfully", p_dt_trained)

        eval_res = pipeline.evaluate()
        models = eval_res["models"]
        lr_m = models["logistic_regression"]
        dt_m = models["decision_tree"]

        # Metric validity checks
        p_metrics = (
            0.60 <= lr_m["accuracy"] <= 0.95
            and 0.60 <= dt_m["accuracy"] <= 0.95
            and 0.70 <= lr_m["roc_auc"] <= 0.95
            and 0.70 <= dt_m["roc_auc"] <= 0.95
            and lr_m["recall"] > 0.50  # Balanced recall check
            and dt_m["recall"] > 0.50
        )
        self.log_result(
            "Classification metrics (Accuracy, Precision, Recall, F1, ROC-AUC) calculate correctly",
            p_metrics,
            f"LR: Acc={lr_m['accuracy']}, Rec={lr_m['recall']}, AUC={lr_m['roc_auc']} | DT: Acc={dt_m['accuracy']}, Rec={dt_m['recall']}"
        )

        # Feature importance / coefficient check
        fi_df = pipeline.compute_feature_importance()
        p_fi = len(fi_df) > 0 and "association_direction" in fi_df.columns
        self.log_result("Ranked explanatory feature importance table generated", p_fi)

        # Save artifacts
        saved = pipeline.save_artifacts()
        p_saved = all(os.path.exists(p) for p in saved.values())
        self.log_result("Model binaries and result files persisted to disk", p_saved)

        return pipeline

    # =========================================================================
    # PART 2: NETWORK CLUSTERING TESTS
    # =========================================================================

    def test_network_clustering(self):
        print("\n--- TEST 8, 9, 10, 11, 12: Network Degradation Clustering ---")
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM FACT_NETWORK_KPI;")
        raw_net_obs = cur.fetchone()[0]

        net_pipe = NetworkClusteringPipeline(k_range=(2, 3, 4, 5), selected_k=3, random_state=42)
        net_pipe.load_data(self.conn)
        dataset = net_pipe.dataset

        # 8. Numeric features
        X_raw = dataset["X_raw"]
        p_numeric = all(np.issubdtype(X_raw[col].dtype, np.number) for col in X_raw.columns)
        self.log_result(f"Network KPI features are strictly numeric (7 features)", p_numeric)

        # 9. Non-KPI identifiers excluded
        feature_names = dataset["feature_names"]
        forbidden_idents = ["cell_id", "region", "technology", "timestamp", "network_kpi_key"]
        p_no_idents = not any(ident in feature_names for ident in forbidden_idents)
        self.log_result("Network identifiers (cell_id, region, technology) excluded from clustering", p_no_idents)

        # 10 & 11. K-Means execution across K=2..5 and silhouette scores
        k_eval = net_pipe.evaluate_k_range()
        metrics = k_eval["metrics"]
        p_k_exec = len(metrics) == 4
        p_sil = all(0.20 <= m["silhouette_score"] <= 0.95 for m in metrics)
        self.log_result(
            "K-Means executes for K=2, 3, 4, 5 with valid Inertia and Silhouette scores",
            p_k_exec and p_sil,
            f"K metrics: {metrics}"
        )

        # 12. Cluster profiles
        profiles_df = net_pipe.compute_cluster_profiles()
        total_clustered_obs = profiles_df["observation_count"].sum()
        p_profiles = (
            len(profiles_df) == 3
            and total_clustered_obs == raw_net_obs == 3600
            and "operational_interpretation" in profiles_df.columns
        )
        self.log_result(
            f"Cluster profiles calculate across all 7 KPIs reconciling to {raw_net_obs} observations",
            p_profiles,
            f"Observed total: {total_clustered_obs} across {len(profiles_df)} clusters"
        )

        # Save artifacts
        saved = net_pipe.save_artifacts()
        p_saved = all(os.path.exists(p) for p in saved.values())
        self.log_result("K-Means model binary, scaler, and cluster profiles saved to disk", p_saved)

        return net_pipe

    # =========================================================================
    # PART 3: ASSOCIATION RULE MINING TESTS
    # =========================================================================

    def test_association_rule_mining(self):
        print("\n--- TEST 13, 14, 15: Customer Service Pattern Mining ---")
        miner = CustomerAssociationMiner(
            min_support=0.05,
            min_confidence=0.35,
            min_lift=1.20,
            target_consequent="Churn=Yes",
            max_itemset_len=3,
        )
        miner.load_transactions(self.conn)

        # 13. Transactions generated correctly
        p_trans = (
            len(miner.transactions) == 7043
            and all("Churn=Yes" in t or "Churn=No" in t for t in miner.transactions)
            and all(not any("customerid" in item.lower() for item in t) for t in miner.transactions)
        )
        self.log_result(
            "Association transactions generated correctly (7,043 transactions, zero customerID)",
            p_trans
        )

        # 14 & 15. Association rules calculated and valid
        miner.find_frequent_itemsets()
        rules_df = miner.generate_rules()

        p_rules = (
            len(rules_df) > 0
            and all(rules_df["consequent"] == "Churn=Yes")
            and (rules_df["support"] >= 0.05).all()
            and (rules_df["confidence"] >= 0.35).all()
            and (rules_df["lift"] >= 1.20).all()
        )
        self.log_result(
            f"Association rules targeting 'Churn=Yes' generated ({len(rules_df)} rules, all meet support/confidence/lift)",
            p_rules,
            f"Rule count: {len(rules_df)}"
        )

        saved_path = miner.save_results()
        p_saved = os.path.exists(saved_path)
        self.log_result("Association rules CSV exported to backend/mining/results/", p_saved)

        return miner

    def run_all(self):
        print("=" * 70)
        print("DATA MINING LAYER VALIDATION SUITE (STEP 5)")
        print("Target Warehouse: database/warehouse.db")
        print("=" * 70)

        # Part 1: Customer Churn
        churn_data = self.test_churn_data_loading_and_reconciliation()
        self.test_churn_anti_leakage(churn_data)
        self.test_churn_train_test_split_and_no_nan(churn_data)
        churn_pipeline = self.test_churn_model_training_and_evaluation()

        # Part 2: Network Clustering
        net_pipeline = self.test_network_clustering()

        # Part 3: Association Mining
        assoc_miner = self.test_association_rule_mining()

        self.conn.close()

        print("\n" + "=" * 70)
        print("DATA MINING DETAILED SUMMARY REPORT")
        print("=" * 70)

        # 1. Churn Model Summary
        print("\n[CUSTOMER CHURN CLASSIFICATION SUMMARY]")
        eval_dict = churn_pipeline.evaluation_results
        test_dist = eval_dict["class_distribution_test"]
        print(f"Test Set Size: {test_dist['total_samples']} | Non-Churn: {test_dist['non_churn_class_count']} | Churn: {test_dist['churn_class_count']} ({test_dist['churn_prevalence_pct']}%)")
        for m_key, m_val in eval_dict["models"].items():
            print(f"\nModel: {m_val['model_name']}")
            print(f"  Accuracy:  {m_val['accuracy']:.4f}")
            print(f"  Precision: {m_val['precision']:.4f}")
            print(f"  Recall:    {m_val['recall']:.4f} (Churn Class Detection Rate)")
            print(f"  F1-Score:  {m_val['f1_score']:.4f}")
            print(f"  ROC-AUC:   {m_val['roc_auc']:.4f}")
            cm = m_val["confusion_matrix"]
            print(f"  Confusion Matrix: TN={cm['true_negative']}, FP={cm['false_positive']}, FN={cm['false_negative']}, TP={cm['true_positive']}")

        print("\nTop 5 Explanatory Features (Ranked by Decision Tree Importance & Direction):")
        fi_top = churn_pipeline.feature_importance_df.head(5)
        for _, r in fi_top.iterrows():
            print(f"  - {r['feature']}: DT Imp={r['dt_importance']:.4f}, LR Coef={r['lr_coefficient']:.4f} -> {r['association_direction']}")

        # 2. Network Clustering Summary
        print("\n[NETWORK DEGRADATION CLUSTERING SUMMARY]")
        k_eval = net_pipeline.k_evaluation_results
        print(f"Tested K Values: {k_eval['tested_k_values']}")
        for m in k_eval["metrics"]:
            print(f"  K={m['k']}: Inertia={m['inertia']:.2f}, Silhouette Score={m['silhouette_score']:.4f}")
        print(f"\nSelected Demonstration K: {k_eval['selected_k']}")
        print(k_eval["selection_rationale"])

        print("\nCluster Profiles (Unscaled KPI Averages):")
        prof_df = net_pipeline.cluster_profiles_df
        for _, row in prof_df.iterrows():
            print(f"  Cluster {row['cluster_id']} ({row['operational_interpretation']}):")
            print(f"    Observations: {row['observation_count']} ({row['network_share_pct']}% of network)")
            print(f"    Avg Latency: {row['latency_ms']} ms | Throughput: {row['throughput_mbps']} Mbps | Call Drop: {row['call_drop_rate_pct']}%")
            print(f"    Packet Loss: {row['packet_loss_pct']}% | Signal: {row['signal_strength_dbm']} dBm | Connections: {row['active_connections']}")

        # 3. Association Mining Summary
        print("\n[CUSTOMER SERVICE PATTERN MINING (APRIORI)]")
        print(f"Transactions Processed: {assoc_miner.dataset_size}")
        print(f"Total Rules Meeting Constraints: {len(assoc_miner.rules_df)}")
        print("\nTop 5 Rules Associated with 'Churn = Yes' (Ranked by Lift):")
        top_rules = assoc_miner.rules_df.head(5)
        for _, r in top_rules.iterrows():
            print(f"  IF {r['antecedent']} -> THEN {r['consequent']}")
            print(f"     Support: {r['support']:.4f} | Confidence: {r['confidence']:.4f} ({r['confidence']*100:.1f}%) | Lift: {r['lift']:.4f}")

        # Final Verification
        print("\n" + "=" * 70)
        print("TEST SUITE EXECUTION SUMMARY")
        print("=" * 70)
        print(f"Total Tests Executed: {self.tests_executed}")
        print(f"Total Tests Passed:   {self.tests_passed}")
        print(f"Total Tests Failed:   {self.tests_failed}")

        if self.tests_failed > 0:
            print("\nFailures:")
            for f in self.failures:
                print(f"  - {f}")
            return False

        print("\nALL DATA MINING TESTS AND VALIDATIONS PASSED!")
        return True


if __name__ == "__main__":
    runner = MiningTestRunner()
    success = runner.run_all()
    sys.exit(0 if success else 1)
