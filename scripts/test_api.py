"""
FastAPI Backend REST API Test & Validation Suite
Validates all 24 required test cases across Health, Cells, Network,
OLAP, Data Mining, and Network Simulation routes using FastAPI TestClient.
Enforces pre- and post-test warehouse database immutability verification.
"""

import os
import sqlite3
import sys
from typing import Any, Dict, List

# Add workspace root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Ensure stdout handles UTF-8 gracefully if supported
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi.testclient import TestClient
from backend.api.main import app
from backend.olap.queries import get_connection


class ApiTestRunner:
    """Orchestrates comprehensive validation tests for the REST API service layer."""

    def __init__(self):
        self.client = TestClient(app)
        self.conn = get_connection()
        self.tests_executed = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures: List[str] = []

        # Record pre-test database snapshot
        self.pre_db_state = self._get_db_state_snapshot()

    def _get_db_state_snapshot(self) -> Dict[str, Any]:
        """Captures database row counts and PRAGMA integrity check."""
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM FACT_NETWORK_KPI;")
        net_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM FACT_CUSTOMER_CHURN;")
        cust_count = cur.fetchone()[0]

        cur.execute("PRAGMA integrity_check;")
        integrity = cur.fetchone()[0]

        return {
            "fact_network_kpi_count": net_count,
            "fact_customer_churn_count": cust_count,
            "integrity_check": integrity,
        }

    def _record_result(self, test_name: str, passed: bool, detail: str = ""):
        self.tests_executed += 1
        if passed:
            self.tests_passed += 1
            print(f"  [PASS] Check {self.tests_executed:02d}: {test_name}")
            if detail:
                print(f"         +-- {detail}")
        else:
            self.tests_failed += 1
            msg = f"Check {self.tests_executed:02d} FAILED: {test_name} - {detail}"
            self.failures.append(msg)
            print(f"  [FAIL] {msg}")

    # -------------------------------------------------------------------------
    # TEST SUITE IMPLEMENTATION
    # -------------------------------------------------------------------------
    def run_all_tests(self):
        print("\n" + "=" * 80)
        print("  STEP 7: BACKEND REST API SERVICE LAYER VALIDATION SUITE")
        print("=" * 80)

        # Check 1: GET /api/health
        try:
            res = self.client.get("/api/health")
            data = res.json()
            passed = (
                res.status_code == 200
                and data.get("status") == "ok"
                and data.get("database") == "connected"
            )
            self._record_result("GET /api/health", passed, f"Status={res.status_code}, Body={data}")
        except Exception as e:
            self._record_result("GET /api/health", False, str(e))

        # Check 2: GET /api/cells
        try:
            res = self.client.get("/api/cells")
            body = res.json()
            cells = body.get("data", [])
            passed = res.status_code == 200 and body.get("success") is True and len(cells) > 0
            self._record_result("GET /api/cells", passed, f"Status={res.status_code}, Returned {len(cells)} cells")
        except Exception as e:
            self._record_result("GET /api/cells", False, str(e))

        # Check 3: GET /api/cells?region=Central
        try:
            res = self.client.get("/api/cells?region=Central")
            body = res.json()
            cells = body.get("data", [])
            all_central = all(c.get("region") == "Central" for c in cells)
            passed = res.status_code == 200 and len(cells) > 0 and all_central
            self._record_result(
                "GET /api/cells?region=Central",
                passed,
                f"Status={res.status_code}, Filtered {len(cells)} Central cells; All verified = {all_central}",
            )
        except Exception as e:
            self._record_result("GET /api/cells?region=Central", False, str(e))

        # Check 4: GET /api/cells?technology=5G
        try:
            res = self.client.get("/api/cells?technology=5G")
            body = res.json()
            cells = body.get("data", [])
            all_5g = all(c.get("technology") == "5G" for c in cells)
            passed = res.status_code == 200 and len(cells) > 0 and all_5g
            self._record_result(
                "GET /api/cells?technology=5G",
                passed,
                f"Status={res.status_code}, Filtered {len(cells)} 5G cells; All verified = {all_5g}",
            )
        except Exception as e:
            self._record_result("GET /api/cells?technology=5G", False, str(e))

        # Check 5: GET /api/cells/Cell_0025
        try:
            res = self.client.get("/api/cells/Cell_0025")
            body = res.json()
            detail = body.get("data", {})
            passed = (
                res.status_code == 200
                and detail.get("cell_id") == "Cell_0025"
                and detail.get("region") == "Central"
                and detail.get("technology") == "5G"
                and detail.get("available_observation_count") == 30
            )
            self._record_result(
                "GET /api/cells/Cell_0025",
                passed,
                f"Cell_0025 verified: Region={detail.get('region')}, Tech={detail.get('technology')}, Observations={detail.get('available_observation_count')}",
            )
        except Exception as e:
            self._record_result("GET /api/cells/Cell_0025", False, str(e))

        # Check 6: GET /api/cells/invalid-cell returns 404
        try:
            res = self.client.get("/api/cells/Cell_999999")
            body = res.json()
            passed = res.status_code == 404 and body.get("success") is False and "error" in body
            self._record_result(
                "GET /api/cells/invalid-cell returns 404",
                passed,
                f"Status={res.status_code}, Error code={body.get('error', {}).get('code')}",
            )
        except Exception as e:
            self._record_result("GET /api/cells/invalid-cell returns 404", False, str(e))

        # Check 7: GET /api/network/Cell_0025
        try:
            res = self.client.get("/api/network/Cell_0025?limit=10")
            body = res.json()
            obs = body.get("data", [])
            passed = res.status_code == 200 and len(obs) == 10 and obs[0].get("cell_id") == "Cell_0025"
            self._record_result(
                "GET /api/network/Cell_0025",
                passed,
                f"Status={res.status_code}, Retrieved {len(obs)} observations (e.g. latency={obs[0].get('latency_ms')}ms)",
            )
        except Exception as e:
            self._record_result("GET /api/network/Cell_0025", False, str(e))

        # Check 8: GET /api/network/Cell_0025/summary
        try:
            res = self.client.get("/api/network/Cell_0025/summary")
            body = res.json()
            data = body.get("data", {})
            passed = (
                res.status_code == 200
                and data.get("cell_id") == "Cell_0025"
                and data.get("observation_count") == 30
                and "average_latency_ms" in data
                and "metrics" in data
            )
            self._record_result(
                "GET /api/network/Cell_0025/summary",
                passed,
                f"Summary verified: Avg Latency={data.get('average_latency_ms')}ms, Avg Tput={data.get('average_throughput_mbps')}Mbps",
            )
        except Exception as e:
            self._record_result("GET /api/network/Cell_0025/summary", False, str(e))

        # Check 9: OLAP summary endpoints
        try:
            res_cust = self.client.get("/api/olap/customer/summary")
            res_net = self.client.get("/api/olap/network/summary")
            body_cust = res_cust.json().get("data", {})
            body_net = res_net.json().get("data", {})
            passed = (
                res_cust.status_code == 200
                and res_net.status_code == 200
                and body_cust.get("operation") == "customer_summary"
                and body_net.get("operation") == "network_summary"
            )
            self._record_result(
                "OLAP summary endpoints (Customer & Network)",
                passed,
                f"Customer Churn Rate={body_cust.get('results', {}).get('churn_rate_pct')}%, "
                f"Network Total Observations={body_net.get('results', {}).get('total_observations')}",
            )
        except Exception as e:
            self._record_result("OLAP summary endpoints", False, str(e))

        # Check 10: Mining summary endpoint
        try:
            res = self.client.get("/api/mining/summary")
            body = res.json()
            data = body.get("data", {})
            passed = (
                res.status_code == 200
                and data.get("simulated") is False
                and "customer_churn" in data
                and "network_clustering" in data
                and "association_rules" in data
            )
            self._record_result(
                "Mining summary endpoint",
                passed,
                f"Status={res.status_code}, Supervised models={data.get('customer_churn', {}).get('models_trained')}",
            )
        except Exception as e:
            self._record_result("Mining summary endpoint", False, str(e))

        # Check 11: Mining churn endpoint
        try:
            res = self.client.get("/api/mining/churn")
            body = res.json()
            data = body.get("data", {})
            passed = (
                res.status_code == 200
                and data.get("simulated") is False
                and "evaluation_metrics" in data
                and len(data.get("feature_importances", [])) > 0
            )
            lr_auc = data.get("evaluation_metrics", {}).get("logistic_regression", {}).get("roc_auc")
            self._record_result(
                "Mining churn endpoint",
                passed,
                f"Status={res.status_code}, Logistic Regression ROC-AUC={lr_auc}, Features count={len(data.get('feature_importances', []))}",
            )
        except Exception as e:
            self._record_result("Mining churn endpoint", False, str(e))

        # Check 12: Mining clustering endpoint
        try:
            res = self.client.get("/api/mining/clusters")
            body = res.json()
            data = body.get("data", {})
            passed = (
                res.status_code == 200
                and data.get("simulated") is False
                and data.get("selected_k") == 3
                and len(data.get("cluster_profiles", [])) == 3
            )
            self._record_result(
                "Mining clustering endpoint",
                passed,
                f"Status={res.status_code}, Selected K={data.get('selected_k')}, Profiles count={len(data.get('cluster_profiles', []))}",
            )
        except Exception as e:
            self._record_result("Mining clustering endpoint", False, str(e))

        # Check 13: Mining association rules endpoint
        try:
            res = self.client.get("/api/mining/association-rules?limit=10")
            body = res.json()
            data = body.get("data", {})
            rules = data.get("rules", [])
            passed = (
                res.status_code == 200
                and data.get("simulated") is False
                and len(rules) > 0
                and all("consequent" in r and "lift" in r for r in rules)
            )
            top_rule = rules[0] if rules else {}
            self._record_result(
                "Mining association rules endpoint",
                passed,
                f"Status={res.status_code}, Returned {len(rules)} rules, Top lift={top_rule.get('lift')}",
            )
        except Exception as e:
            self._record_result("Mining association rules endpoint", False, str(e))

        # Check 14: Simulation state endpoint
        try:
            res = self.client.get("/api/simulation/state")
            body = res.json()
            data = body.get("data", {})
            passed = (
                res.status_code == 200
                and data.get("simulation") is True
                and "cell" in data
                and "health_score" in data
                and "baseline" in data
                and "current" in data
            )
            self._record_result(
                "Simulation state endpoint",
                passed,
                f"Status={res.status_code}, Cell={data.get('cell', {}).get('cell_id')}, Health={data.get('health_score')}",
            )
        except Exception as e:
            self._record_result("Simulation state endpoint", False, str(e))

        # Check 15: Simulation select-cell
        try:
            res = self.client.post("/api/simulation/select-cell", json={"cell_id": "Cell_0005"})
            body = res.json()
            data = body.get("data", {})
            passed = (
                res.status_code == 200
                and data.get("cell", {}).get("cell_id") == "Cell_0005"
                and data.get("cell", {}).get("region") == "Central"
            )
            self._record_result(
                "Simulation select-cell (Cell_0005)",
                passed,
                f"Status={res.status_code}, Selected Cell_0005: Region={data.get('cell', {}).get('region')}, Baseline Latency={data.get('baseline', {}).get('latency_ms')}ms",
            )
            # Revert to default Cell_0025
            self.client.post("/api/simulation/select-cell", json={"cell_id": "Cell_0025"})
        except Exception as e:
            self._record_result("Simulation select-cell", False, str(e))

        # Check 16: Simulation scenario
        try:
            res = self.client.post("/api/simulation/scenario", json={"scenario": "CONGESTION", "severity": "HIGH"})
            body = res.json()
            data = body.get("data", {})
            passed = (
                res.status_code == 200
                and data.get("scenario") == "CONGESTION"
                and data.get("severity") == "HIGH"
                and data.get("simulation") is True
            )
            self._record_result(
                "Simulation scenario (CONGESTION / HIGH)",
                passed,
                f"Status={res.status_code}, Scenario applied: {data.get('scenario')} ({data.get('severity')})",
            )
        except Exception as e:
            self._record_result("Simulation scenario", False, str(e))

        # Check 17: Simulation update
        try:
            res = self.client.post("/api/simulation/update", json={"delta_time": 2.5})
            body = res.json()
            data = body.get("data", {})
            passed = (
                res.status_code == 200
                and data.get("simulation_time") >= 2.5
                and "current" in data
            )
            self._record_result(
                "Simulation update (delta_time=2.5s)",
                passed,
                f"Status={res.status_code}, Advanced simulation_time={data.get('simulation_time')}s, Health={data.get('health_score')}",
            )
        except Exception as e:
            self._record_result("Simulation update", False, str(e))

        # Check 18: Simulation comparison
        try:
            res = self.client.get("/api/simulation/comparison")
            body = res.json()
            comps = body.get("data", [])
            passed = res.status_code == 200 and len(comps) == 7 and all("absolute_difference" in c for c in comps)
            self._record_result(
                "Simulation comparison",
                passed,
                f"Status={res.status_code}, Verified {len(comps)} delta metric rows",
            )
        except Exception as e:
            self._record_result("Simulation comparison", False, str(e))

        # Check 19: Simulation reset
        try:
            res = self.client.post("/api/simulation/reset")
            body = res.json()
            data = body.get("data", {})
            passed = (
                res.status_code == 200
                and data.get("simulation_time") == 0.0
                and data.get("scenario") == "NORMAL"
            )
            self._record_result(
                "Simulation reset",
                passed,
                f"Status={res.status_code}, Restored pristine baseline: simulation_time={data.get('simulation_time')}s, Health={data.get('health_score')}",
            )
        except Exception as e:
            self._record_result("Simulation reset", False, str(e))

        # Check 20: Simulation events
        try:
            # Generate event, check GET, then DELETE
            self.client.post("/api/simulation/pause")
            res_get = self.client.get("/api/simulation/events")
            events = res_get.json().get("data", [])
            res_del = self.client.delete("/api/simulation/events")
            res_get_after = self.client.get("/api/simulation/events")
            events_after = res_get_after.json().get("data", [])

            self.client.post("/api/simulation/resume")

            passed = (
                res_get.status_code == 200
                and len(events) > 0
                and res_del.status_code == 200
                and len(events_after) == 0
            )
            self._record_result(
                "Simulation events (GET & DELETE)",
                passed,
                f"Recorded {len(events)} events; Successfully cleared (count after delete = {len(events_after)})",
            )
        except Exception as e:
            self._record_result("Simulation events", False, str(e))

        # Check 21: Invalid scenario returns 400
        try:
            res = self.client.post("/api/simulation/scenario", json={"scenario": "EARTHQUAKE", "severity": "HIGH"})
            body = res.json()
            passed = res.status_code == 400 and body.get("success") is False and "INVALID_SCENARIO" in body.get("error", {}).get("code", "")
            self._record_result(
                "Invalid scenario returns 400",
                passed,
                f"Status={res.status_code}, Error code={body.get('error', {}).get('code')}",
            )
        except Exception as e:
            self._record_result("Invalid scenario returns 400", False, str(e))

        # Check 22: Invalid severity returns 400
        try:
            res = self.client.post("/api/simulation/scenario", json={"scenario": "CONGESTION", "severity": "MAXIMUM_OVERDRIVE"})
            body = res.json()
            passed = res.status_code == 400 and body.get("success") is False and "INVALID_SEVERITY" in body.get("error", {}).get("code", "")
            self._record_result(
                "Invalid severity returns 400",
                passed,
                f"Status={res.status_code}, Error code={body.get('error', {}).get('code')}",
            )
        except Exception as e:
            self._record_result("Invalid severity returns 400", False, str(e))

        # Check 23: Invalid delta_time returns 400
        try:
            res_neg = self.client.post("/api/simulation/update", json={"delta_time": -5.0})
            res_huge = self.client.post("/api/simulation/update", json={"delta_time": 1000.0})
            passed = res_neg.status_code == 400 and res_huge.status_code == 400
            self._record_result(
                "Invalid delta_time returns 400",
                passed,
                f"Negative delta -> HTTP {res_neg.status_code}; Huge delta (>60s) -> HTTP {res_huge.status_code}",
            )
        except Exception as e:
            self._record_result("Invalid delta_time returns 400", False, str(e))

        # Check 24: Database remains unchanged
        try:
            post_db_state = self._get_db_state_snapshot()
            counts_intact = (
                post_db_state["fact_network_kpi_count"] == self.pre_db_state["fact_network_kpi_count"] == 3600
                and post_db_state["fact_customer_churn_count"]
                == self.pre_db_state["fact_customer_churn_count"]
                == 7043
            )
            integrity_ok = (
                post_db_state["integrity_check"] == self.pre_db_state["integrity_check"] == "ok"
            )
            passed = counts_intact and integrity_ok
            self._record_result(
                "Database remains unchanged (3,600 network rows, 7,043 churn rows, integrity=ok)",
                passed,
                f"FACT_NETWORK_KPI={post_db_state['fact_network_kpi_count']} (expected 3600), "
                f"FACT_CUSTOMER_CHURN={post_db_state['fact_customer_churn_count']} (expected 7043), "
                f"PRAGMA integrity_check='{post_db_state['integrity_check']}'",
            )
        except Exception as e:
            self._record_result("Database remains unchanged", False, str(e))

        print("\n" + "-" * 80)
        print(f"  RESULTS: {self.tests_passed}/{self.tests_executed} checks passed.")
        if self.tests_failed > 0:
            print(f"  FAILURES ({self.tests_failed}):")
            for f in self.failures:
                print(f"    - {f}")
        print("-" * 80)
        return self.tests_failed == 0


if __name__ == "__main__":
    runner = ApiTestRunner()
    success = runner.run_all_tests()
    sys.exit(0 if success else 1)
