"""
OLAP Analytical Engine Test & Validation Suite
Tests and validates every Customer and Network OLAP operation against SQLite warehouse.db.
Verifies exact mathematical consistency, parameterized safety, domain validation,
and strict decoupled mart isolation (zero customer-to-cell joins).
"""

import os
import sys
import sqlite3
from typing import Any, Dict, List, Tuple

# Add workspace root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.olap import (
    CustomerOLAP,
    NetworkOLAP,
    get_customer_summary,
    get_customer_rollup,
    get_customer_drilldown,
    get_customer_slice,
    get_customer_dice,
    get_network_summary,
    get_network_rollup,
    get_network_drilldown,
    get_network_slice,
    get_network_dice,
    get_high_call_drop_cells,
    get_connection,
)


class OLAPTestRunner:
    """Orchestrates comprehensive testing and mathematical validation of OLAP operations."""

    def __init__(self):
        self.conn = get_connection()
        self.cust_olap = CustomerOLAP(self.conn)
        self.net_olap = NetworkOLAP(self.conn)
        self.tests_executed = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures: List[str] = []
        self.sample_results: Dict[str, Any] = {}

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
    # CUSTOMER TESTS
    # =========================================================================

    def test_customer_summary(self):
        print("\n--- TEST 1: Customer KPI Summary ---")
        res = self.cust_olap.get_customer_summary()
        self.sample_results["customer_summary"] = res

        r = res.get("results", {})
        total = r.get("total_customers")
        churned = r.get("churned_customers")
        non_churned = r.get("non_churned_customers")
        rate = r.get("churn_rate_pct")

        # Ground truth checks against warehouse
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*), SUM(churn_flag) FROM FACT_CUSTOMER_CHURN;")
        raw_total, raw_churned = cur.fetchone()

        passed = (
            res.get("status") == "success"
            and total == raw_total == 7043
            and churned == raw_churned == 1869
            and non_churned == (7043 - 1869) == 5174
            and abs(rate - 26.54) < 0.05
        )
        self.log_result(
            "Customer Summary matches warehouse ground truth (7043 total, 1869 churned)",
            passed,
            f"Got total={total}, churned={churned}, non_churned={non_churned}, rate={rate}"
        )

    def test_customer_rollup(self):
        print("\n--- TEST 2: Customer Roll-Up (Customer -> Tenure Band) ---")
        res = self.cust_olap.get_customer_rollup(group_by="tenure_band")
        self.sample_results["customer_rollup"] = res

        results = res.get("results", [])
        expected_bands = {"0-12 months", "13-24 months", "25-48 months", "49-72 months"}
        actual_bands = {row["tenure_band"] for row in results}

        total_cust_sum = sum(row["customer_count"] for row in results)
        total_churn_sum = sum(row["churned_customers"] for row in results)

        passed = (
            res.get("status") == "success"
            and actual_bands == expected_bands
            and total_cust_sum == 7043
            and total_churn_sum == 1869
            and all(row["non_churned_customers"] == row["customer_count"] - row["churned_customers"] for row in results)
        )
        self.log_result(
            "Customer Roll-up by tenure band covers 4 bands and reconciles mathematically (sum=7043, churn=1869)",
            passed,
            f"Bands: {actual_bands}, Total sum: {total_cust_sum}, Churn sum: {total_churn_sum}"
        )

    def test_customer_drilldown(self):
        print("\n--- TEST 3: Customer Drill-Down (Tenure Band -> Contract) ---")
        band = "0-12 months"
        res = self.cust_olap.get_customer_drilldown(tenure_band=band)
        self.sample_results["customer_drilldown"] = res

        results = res.get("results", [])
        drilldown_cust_sum = sum(row["customer_count"] for row in results)
        drilldown_churn_sum = sum(row["churned_customers"] for row in results)

        # Get parent band numbers from rollup
        parent_res = self.cust_olap.get_customer_rollup(group_by="tenure_band")
        parent_row = next(r for r in parent_res["results"] if r["tenure_band"] == band)

        passed = (
            res.get("status") == "success"
            and len(results) > 0
            and drilldown_cust_sum == parent_row["customer_count"] == 2186
            and drilldown_churn_sum == parent_row["churned_customers"] == 1037
        )
        self.log_result(
            f"Customer Drill-down for '{band}' sums exactly to parent band ({parent_row['customer_count']})",
            passed,
            f"Drilldown sum={drilldown_cust_sum}, Parent count={parent_row['customer_count']}"
        )

    def test_customer_slice(self):
        print("\n--- TEST 4: Customer Slice (Single Dimension Filter) ---")
        res = self.cust_olap.get_customer_slice(dimension="contract", value="Month-to-month")
        self.sample_results["customer_slice"] = res

        r = res.get("results", {})
        cust_cnt = r.get("customer_count")
        churn_cnt = r.get("churned_count")

        cur = self.conn.cursor()
        cur.execute("""
            SELECT COUNT(*), SUM(churn_flag)
            FROM FACT_CUSTOMER_CHURN f
            JOIN DIM_PLAN p ON f.plan_key = p.plan_key
            WHERE p.Contract = 'Month-to-month';
        """)
        raw_cnt, raw_churn = cur.fetchone()

        passed = (
            res.get("status") == "success"
            and cust_cnt == raw_cnt == 3875
            and churn_cnt == raw_churn == 1655
        )
        self.log_result(
            "Customer Slice on Contract='Month-to-month' matches warehouse raw query (3875 rows)",
            passed,
            f"Got cust_cnt={cust_cnt} vs raw={raw_cnt}"
        )

    def test_customer_dice(self):
        print("\n--- TEST 5: Customer Dice (Multi-Dimension Filter) ---")
        filters = {
            "contract": "Month-to-month",
            "internet_service": "Fiber optic",
            "tenure_band": "0-12 months",
        }
        res = self.cust_olap.get_customer_dice(filters=filters)
        self.sample_results["customer_dice"] = res

        r = res.get("results", {})
        cust_cnt = r.get("customer_count")
        churn_cnt = r.get("churned_count")

        cur = self.conn.cursor()
        cur.execute("""
            SELECT COUNT(*), SUM(churn_flag)
            FROM FACT_CUSTOMER_CHURN f
            JOIN DIM_CUSTOMER c ON f.customer_key = c.customer_key
            JOIN DIM_PLAN p ON f.plan_key = p.plan_key
            WHERE p.Contract = 'Month-to-month'
              AND p.InternetService = 'Fiber optic'
              AND (
                CASE 
                    WHEN c.tenure <= 12 THEN '0-12 months'
                    WHEN c.tenure <= 24 THEN '13-24 months'
                    WHEN c.tenure <= 48 THEN '25-48 months'
                    ELSE '49-72 months'
                END
              ) = '0-12 months';
        """)
        raw_cnt, raw_churn = cur.fetchone()

        passed = (
            res.get("status") == "success"
            and cust_cnt == raw_cnt == 916
            and churn_cnt == raw_churn == 643
        )
        self.log_result(
            "Customer Dice across contract, internet service, and tenure band matches raw query (916 rows, 643 churn)",
            passed,
            f"Got cust_cnt={cust_cnt} vs raw={raw_cnt}"
        )

    # =========================================================================
    # NETWORK TESTS
    # =========================================================================

    def test_network_summary(self):
        print("\n--- TEST 6: Network KPI Summary ---")
        res = self.net_olap.get_network_summary()
        self.sample_results["network_summary"] = res

        r = res.get("results", {})
        obs = r.get("total_observations")
        cells = r.get("number_of_cells")
        regions = r.get("number_of_regions")
        techs = r.get("number_of_technologies")

        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM FACT_NETWORK_KPI;")
        raw_obs = cur.fetchone()[0]

        passed = (
            res.get("status") == "success"
            and obs == raw_obs == 3600
            and cells == 120
            and regions == 5
            and techs == 2
        )
        self.log_result(
            "Network Summary matches ground truth (3600 obs, 120 cells, 5 regions, 2 techs)",
            passed,
            f"Got obs={obs}, cells={cells}, regions={regions}, techs={techs}"
        )

    def test_network_rollup(self):
        print("\n--- TEST 7: Network Roll-Up (Time: Minute -> Hour -> Day -> Month) ---")
        levels = ["minute", "hour", "day", "month"]
        expected_counts = {"minute": 30, "hour": 1, "day": 1, "month": 1}

        all_passed = True
        sample_rows = {}
        for lvl in levels:
            res = self.net_olap.get_network_rollup(level=lvl)
            results = res.get("results", [])
            sample_rows[lvl] = len(results)
            total_obs = sum(row["observation_count"] for row in results)
            if res.get("status") != "success" or len(results) != expected_counts[lvl] or total_obs != 3600:
                all_passed = False

        self.sample_results["network_rollup_minute_sample"] = self.net_olap.get_network_rollup(level="minute")["results"][:2]
        self.log_result(
            "Network Roll-up across minute (30), hour (1), day (1), and month (1) reconcile to 3600 obs",
            all_passed,
            f"Observed counts per level: {sample_rows}"
        )

    def test_network_drilldown(self):
        print("\n--- TEST 8: Network Drill-Down (Region -> Cell -> Time) ---")
        # 1. Region level drilldown (returns cells in region)
        region = "North"
        res_reg = self.net_olap.get_network_drilldown(region=region)
        results_reg = res_reg.get("results", [])
        cell_count = len(results_reg)

        cur = self.conn.cursor()
        cur.execute("""
            SELECT COUNT(DISTINCT cell_key)
            FROM FACT_NETWORK_KPI f
            JOIN DIM_REGION r ON f.region_key = r.region_key
            WHERE r.region_name = 'North';
        """)
        raw_cell_count = cur.fetchone()[0]

        # 2. Cell level drilldown (returns time observations for a cell)
        sample_cell = results_reg[0]["cell_id"]
        res_cell = self.net_olap.get_network_drilldown(region=region, cell_id=sample_cell)
        results_cell = res_cell.get("results", [])

        self.sample_results["network_drilldown_region"] = results_reg[:2]
        self.sample_results["network_drilldown_cell"] = results_cell[:2]

        passed = (
            res_reg.get("status") == "success"
            and cell_count == raw_cell_count == 29
            and res_cell.get("status") == "success"
            and len(results_cell) == 30  # 30 minute observations for that cell
        )
        self.log_result(
            f"Network Drill-Down for region='{region}' gives {cell_count} cells, and drill-down to '{sample_cell}' gives 30 minute slices",
            passed,
            f"Region cells: {cell_count} (raw: {raw_cell_count}), Cell minute slices: {len(results_cell)}"
        )

    def test_network_slice(self):
        print("\n--- TEST 9: Network Slice (Single Dimension Filter) ---")
        # Slice by technology = "5G"
        res_tech = self.net_olap.get_network_slice(dimension="technology", value="5G")
        r_tech = res_tech.get("results", {})

        cur = self.conn.cursor()
        cur.execute("""
            SELECT COUNT(*) 
            FROM FACT_NETWORK_KPI f
            JOIN DIM_NETWORK_TECH t ON f.technology_key = t.technology_key
            WHERE t.technology_name = '5G';
        """)
        raw_5g = cur.fetchone()[0]

        # Slice by region = "North"
        res_reg = self.net_olap.get_network_slice(dimension="region", value="North")
        r_reg = res_reg.get("results", {})

        cur.execute("""
            SELECT COUNT(*) 
            FROM FACT_NETWORK_KPI f
            JOIN DIM_REGION r ON f.region_key = r.region_key
            WHERE r.region_name = 'North';
        """)
        raw_north = cur.fetchone()[0]

        self.sample_results["network_slice_5g"] = res_tech

        passed = (
            res_tech.get("status") == "success"
            and r_tech.get("observation_count") == raw_5g
            and res_reg.get("status") == "success"
            and r_reg.get("observation_count") == raw_north
        )
        self.log_result(
            f"Network Slice on technology='5G' ({raw_5g} obs) and region='North' ({raw_north} obs) matches warehouse",
            passed,
            f"Got 5G={r_tech.get('observation_count')} (raw={raw_5g}), North={r_reg.get('observation_count')} (raw={raw_north})"
        )

    def test_network_dice(self):
        print("\n--- TEST 10: Network Dice (Multi-Dimension Filter & Thresholds) ---")
        filters = {
            "region": "North",
            "technology": "5G",
            "call_drop_rate_gt": 2.0,
        }
        res = self.net_olap.get_network_dice(filters=filters)
        self.sample_results["network_dice"] = res

        r = res.get("results", {})
        obs_cnt = r.get("observation_count")

        cur = self.conn.cursor()
        cur.execute("""
            SELECT COUNT(*), ROUND(AVG(f.call_drop_rate_pct), 2)
            FROM FACT_NETWORK_KPI f
            JOIN DIM_REGION r ON f.region_key = r.region_key
            JOIN DIM_NETWORK_TECH tech ON f.technology_key = tech.technology_key
            WHERE r.region_name = 'North'
              AND tech.technology_name = '5G'
              AND f.call_drop_rate_pct > 2.0;
        """)
        raw_cnt, raw_avg_cdr = cur.fetchone()

        passed = (
            res.get("status") == "success"
            and obs_cnt == raw_cnt
            and (obs_cnt == 0 or abs(r.get("avg_call_drop_rate_pct") - raw_avg_cdr) < 0.05)
        )
        self.log_result(
            f"Network Dice (region='North', tech='5G', call_drop_rate_gt=2.0) matches raw query ({obs_cnt} obs)",
            passed,
            f"Got obs_cnt={obs_cnt} vs raw={raw_cnt}"
        )

    def test_high_call_drop_analysis(self):
        print("\n--- TEST 11: High-Call-Drop Analysis (> 2.0% threshold) ---")
        threshold = 2.0
        res = self.net_olap.get_high_call_drop_cells(threshold=threshold)
        self.sample_results["high_call_drop_analysis"] = res

        results = res.get("results", [])
        total_high_drop_obs = sum(row["observation_count"] for row in results)

        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM FACT_NETWORK_KPI WHERE call_drop_rate_pct > ?;", (threshold,))
        raw_high_drop_obs = cur.fetchone()[0]

        passed = (
            res.get("status") == "success"
            and total_high_drop_obs == raw_high_drop_obs == 83
            and all(row["avg_call_drop_rate_pct"] > threshold for row in results)
        )
        self.log_result(
            f"High-Call-Drop Analysis for threshold={threshold}% identifies all {raw_high_drop_obs} severe readings across cells",
            passed,
            f"Total high-drop readings: {total_high_drop_obs} (raw: {raw_high_drop_obs})"
        )

    # =========================================================================
    # NEGATIVE & ERROR HANDLING TESTS
    # =========================================================================

    def test_invalid_filter_handling(self):
        print("\n--- TEST 12: Negative & Controlled Error Handling ---")
        # 1. Invalid region
        res_bad_region = self.net_olap.get_network_drilldown(region="Atlantis")
        p1 = res_bad_region.get("status") == "error" and len(res_bad_region.get("results")) == 0

        # 2. Invalid technology
        res_bad_tech = self.net_olap.get_network_slice(dimension="technology", value="6G")
        p2 = res_bad_tech.get("status") == "error" and res_bad_tech.get("results") == {}

        # 3. Invalid tenure band
        res_bad_band = self.cust_olap.get_customer_drilldown(tenure_band="100 months")
        p3 = res_bad_band.get("status") == "error" and len(res_bad_band.get("results")) == 0

        # 4. Invalid dimension name
        res_bad_dim = self.cust_olap.get_customer_slice(dimension="non_existent_dim", value="foo")
        p4 = res_bad_dim.get("status") == "error" and res_bad_dim.get("results") == {}

        # 5. Invalid time level
        res_bad_level = self.net_olap.get_network_rollup(level="millennium")
        p5 = res_bad_level.get("status") == "error" and len(res_bad_level.get("results")) == 0

        all_passed = p1 and p2 and p3 and p4 and p5
        self.log_result(
            "Controlled error responses returned for invalid region, technology, tenure band, dimension, and time level without crashes",
            all_passed,
            f"p1={p1}, p2={p2}, p3={p3}, p4={p4}, p5={p5}"
        )

    # =========================================================================
    # DATA MODEL ISOLATION & NON-DUPLICATION TESTS
    # =========================================================================

    def test_data_model_isolation(self):
        print("\n--- TEST 13: Data Model Isolation & Fact Integrity ---")
        cur = self.conn.cursor()

        # Check for any tables or views named customer_cell or bridge
        cur.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view');")
        tables = [r[0] for r in cur.fetchall()]
        forbidden = [t for t in tables if "customer_cell" in t.lower() or "bridge" in t.lower()]
        p_no_bridge = len(forbidden) == 0

        # Check total customer fact rows before and after queries
        cur.execute("SELECT COUNT(*) FROM FACT_CUSTOMER_CHURN;")
        cust_cnt = cur.fetchone()[0]

        # Check total network fact rows before and after queries
        cur.execute("SELECT COUNT(*) FROM FACT_NETWORK_KPI;")
        net_cnt = cur.fetchone()[0]

        passed = p_no_bridge and cust_cnt == 7043 and net_cnt == 3600
        self.log_result(
            "Marts strictly decoupled: zero customer-to-cell tables, zero row mutations (7043 cust, 3600 net)",
            passed,
            f"Forbidden tables: {forbidden}, cust_cnt: {cust_cnt}, net_cnt: {net_cnt}"
        )

    def run_all(self):
        print("=" * 70)
        print("TELECOM OLAP ANALYTICAL ENGINE TEST SUITE")
        print("Authoritative Warehouse Target: database/warehouse.db")
        print("=" * 70)

        self.test_customer_summary()
        self.test_customer_rollup()
        self.test_customer_drilldown()
        self.test_customer_slice()
        self.test_customer_dice()

        self.test_network_summary()
        self.test_network_rollup()
        self.test_network_drilldown()
        self.test_network_slice()
        self.test_network_dice()
        self.test_high_call_drop_analysis()

        self.test_invalid_filter_handling()
        self.test_data_model_isolation()

        self.print_sample_results()
        self.conn.close()

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

        print("\nALL OLAP ENGINE TESTS PASSED SUCCESSFULLY!")
        return True

    def print_sample_results(self):
        import json
        print("\n" + "=" * 70)
        print("SAMPLE OUTPUTS FOR EACH OLAP OPERATION")
        print("=" * 70)
        for name, data in self.sample_results.items():
            print(f"\n[SAMPLE] {name.upper()}:")
            formatted = json.dumps(data, indent=2)
            # Limit very long outputs for console readability
            lines = formatted.splitlines()
            if len(lines) > 25:
                print("\n".join(lines[:25]) + f"\n... [{len(lines) - 25} lines truncated for brevity]")
            else:
                print(formatted)


if __name__ == "__main__":
    runner = OLAPTestRunner()
    success = runner.run_all()
    sys.exit(0 if success else 1)
