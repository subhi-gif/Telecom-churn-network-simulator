"""
Telecom Network Simulation Engine Test & Validation Suite
Validates all 18 functional requirements, database immutability,
discrete-event mechanics, health scoring, alerting, and degradation scenarios.
Includes an interactive demonstration runner walking through simulated scenarios.
"""

import copy
import os
import sqlite3
import sys
from typing import Any, Dict, List, Tuple

# Add workspace root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Ensure stdout handles UTF-8 gracefully if supported
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from backend.olap.queries import get_connection
from backend.simulation import (
    DEFAULT_ALERT_THRESHOLDS,
    KPI_DISPLAY_NAMES,
    KPI_KEYS,
    KPI_PHYSICAL_BOUNDS,
    NetworkState,
    SimulationEngine,
    calculate_health_score,
    calculate_scenario_target,
    clamp_kpi_bounds,
    detect_degradation_alerts,
)


class SimulationTestRunner:
    """Orchestrates comprehensive validation tests for the Telecom Simulation Engine."""

    def __init__(self):
        self.conn = get_connection()
        self.tests_executed = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures: List[str] = []

        # Snapshot pre-simulation database state
        self.pre_db_state = self._get_db_state_snapshot()

    def _get_db_state_snapshot(self) -> Dict[str, Any]:
        """Captures record counts and SQLite integrity check status."""
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
        print("  STEP 6: TELECOM NETWORK SIMULATION ENGINE VALIDATION SUITE")
        print("=" * 80)

        # Test 1: Real cell loading from warehouse
        try:
            engine = SimulationEngine(conn_or_path=self.conn, default_cell_id="Cell_0025")
            state = engine.state
            passed = (
                state is not None
                and state.cell_id == "Cell_0025"
                and state.region == "Central"
                and state.technology == "5G"
            )
            self._record_result(
                "Real cell loading from warehouse (Cell_0025)",
                passed,
                f"Loaded Cell_0025: Region={state.region}, Tech={state.technology}, Time={state.timestamp}",
            )
        except Exception as e:
            self._record_result("Real cell loading from warehouse (Cell_0025)", False, str(e))

        # Test 2: Baseline values reflect actual warehouse record
        try:
            cur = self.conn.cursor()
            cur.execute(
                """
                SELECT f.latency_ms, f.throughput_mbps, f.packet_loss_pct,
                       f.call_drop_rate_pct, f.signal_strength_dbm,
                       f.handover_success_pct, f.active_connections
                FROM FACT_NETWORK_KPI f
                JOIN DIM_CELL c ON f.cell_key = c.cell_key
                JOIN DIM_TIME t ON f.time_key = t.time_key
                WHERE c.cell_id = 'Cell_0025'
                ORDER BY t.timestamp ASC
                LIMIT 1;
                """
            )
            row = cur.fetchone()
            base = engine.state.baseline_values
            match = (
                abs(base["latency_ms"] - round(float(row[0]), 2)) < 1e-4
                and abs(base["throughput_mbps"] - round(float(row[1]), 2)) < 1e-4
                and abs(base["packet_loss_pct"] - round(float(row[2]), 3)) < 1e-4
                and abs(base["call_drop_rate_pct"] - round(float(row[3]), 3)) < 1e-4
                and abs(base["signal_strength_dbm"] - round(float(row[4]), 2)) < 1e-4
                and abs(base["handover_success_pct"] - round(float(row[5]), 2)) < 1e-4
                and base["active_connections"] == int(row[6])
            )
            self._record_result(
                "Baseline values match actual warehouse record",
                match,
                f"Latency={base['latency_ms']}ms, Throughput={base['throughput_mbps']}Mbps, Connections={base['active_connections']}",
            )
        except Exception as e:
            self._record_result("Baseline values match actual warehouse record", False, str(e))

        # Test 3: NORMAL scenario keeps baseline intact
        try:
            engine.reset()
            engine.apply_scenario("NORMAL", "LOW")
            for _ in range(5):
                engine.step(1.0)
            comps = engine.get_comparison()
            max_abs_diff = max(abs(c["absolute_difference"]) for c in comps)
            passed = (max_abs_diff == 0.0) and (engine.state.simulation_time == 5.0)
            self._record_result(
                "NORMAL scenario preserves baseline values perfectly",
                passed,
                f"5 steps evaluated; Maximum deviation from baseline = {max_abs_diff}",
            )
        except Exception as e:
            self._record_result("NORMAL scenario preserves baseline values perfectly", False, str(e))

        # Test 4: CONGESTION directional shifts
        try:
            engine.reset()
            engine.apply_scenario("CONGESTION", "MEDIUM")
            # Step until near convergence
            for _ in range(20):
                engine.step(1.0)
            sim = engine.state.simulated_values
            base = engine.state.baseline_values

            conns_up = sim["active_connections"] > base["active_connections"]
            latency_up = sim["latency_ms"] > base["latency_ms"]
            tput_down = sim["throughput_mbps"] < base["throughput_mbps"]
            loss_up = sim["packet_loss_pct"] > base["packet_loss_pct"]
            drop_up = sim["call_drop_rate_pct"] > base["call_drop_rate_pct"]

            passed = conns_up and latency_up and tput_down and loss_up and drop_up
            self._record_result(
                "CONGESTION directional shifts (conn(+), lat(+), tput(-), loss(+), drop(+))",
                passed,
                f"Conn: {base['active_connections']}->{sim['active_connections']}, "
                f"Lat: {base['latency_ms']}->{sim['latency_ms']}ms, "
                f"Tput: {base['throughput_mbps']}->{sim['throughput_mbps']}Mbps",
            )
        except Exception as e:
            self._record_result("CONGESTION directional shifts", False, str(e))

        # Test 5: SIGNAL_DEGRADATION directional shifts
        try:
            engine.reset()
            engine.apply_scenario("SIGNAL_DEGRADATION", "MEDIUM")
            for _ in range(20):
                engine.step(1.0)
            sim = engine.state.simulated_values
            base = engine.state.baseline_values

            sig_down = sim["signal_strength_dbm"] < base["signal_strength_dbm"]
            loss_up = sim["packet_loss_pct"] > base["packet_loss_pct"]
            drop_up = sim["call_drop_rate_pct"] > base["call_drop_rate_pct"]
            ho_down = sim["handover_success_pct"] < base["handover_success_pct"]

            passed = sig_down and loss_up and drop_up and ho_down
            self._record_result(
                "SIGNAL_DEGRADATION directional shifts (sig(-), loss(+), drop(+), ho(-))",
                passed,
                f"Signal: {base['signal_strength_dbm']}->{sim['signal_strength_dbm']}dBm, "
                f"Loss: {base['packet_loss_pct']}%->{sim['packet_loss_pct']}%, "
                f"Drop: {base['call_drop_rate_pct']}%->{sim['call_drop_rate_pct']}%",
            )
        except Exception as e:
            self._record_result("SIGNAL_DEGRADATION directional shifts", False, str(e))

        # Test 6: CELL_OVERLOAD directional shifts
        try:
            engine.reset()
            engine.apply_scenario("CELL_OVERLOAD", "HIGH")
            for _ in range(20):
                engine.step(1.0)
            sim = engine.state.simulated_values
            base = engine.state.baseline_values

            conns_spike = sim["active_connections"] >= base["active_connections"] * 2.5
            tput_collapse = sim["throughput_mbps"] <= base["throughput_mbps"] * 0.4
            drop_spike = sim["call_drop_rate_pct"] >= 2.0

            passed = conns_spike and tput_collapse and drop_spike
            self._record_result(
                "CELL_OVERLOAD directional shifts (conns spike >=2.5x, tput collapse <=0.4x)",
                passed,
                f"Conn: {base['active_connections']}->{sim['active_connections']} "
                f"({round(sim['active_connections']/base['active_connections'], 2)}x), "
                f"Tput: {base['throughput_mbps']}->{sim['throughput_mbps']}Mbps",
            )
        except Exception as e:
            self._record_result("CELL_OVERLOAD directional shifts", False, str(e))

        # Test 7: RECOVERY brings values back toward baseline
        try:
            # First degrade heavily
            engine.reset()
            engine.apply_scenario("CONGESTION", "HIGH")
            for _ in range(15):
                engine.step(1.0)
            degraded_latency = engine.state.latency_ms

            # Apply recovery
            engine.apply_scenario("RECOVERY", "HIGH")
            distances = []
            for _ in range(15):
                engine.step(1.0)
                distances.append(abs(engine.state.latency_ms - engine.state.baseline_values["latency_ms"]))

            # Confirm monotonic convergence toward baseline
            is_recovering = distances[-1] < distances[0] and distances[-1] < abs(
                degraded_latency - engine.state.baseline_values["latency_ms"]
            )
            self._record_result(
                "RECOVERY brings values back toward baseline",
                is_recovering,
                f"Latency distance to baseline: initial={round(distances[0], 2)}ms -> final={round(distances[-1], 2)}ms",
            )
        except Exception as e:
            self._record_result("RECOVERY brings values back toward baseline", False, str(e))

        # Test 8: reset() restores pristine baseline values
        try:
            # Perturb state
            engine.apply_scenario("SIGNAL_DEGRADATION", "HIGH")
            for _ in range(10):
                engine.step(1.0)
            # Reset
            engine.reset()
            sim = engine.state.simulated_values
            base = engine.state.baseline_values

            all_matched = all(sim[k] == base[k] for k in KPI_KEYS)
            time_reset = engine.state.simulation_time == 0.0
            scen_reset = engine.state.scenario_name == "NORMAL"

            passed = all_matched and time_reset and scen_reset
            self._record_result(
                "reset() restores pristine baseline values and clock",
                passed,
                f"All {len(KPI_KEYS)} KPIs exactly equal baseline; simulation_time={engine.state.simulation_time}",
            )
        except Exception as e:
            self._record_result("reset() restores pristine baseline values", False, str(e))

        # Test 9: pause() and resume() toggle time advancement
        try:
            engine.reset()
            engine.apply_scenario("CONGESTION", "MEDIUM")
            engine.step(1.0)
            t_before = engine.state.simulation_time
            val_before = engine.state.latency_ms

            # Pause
            engine.pause()
            self.assertTrue = engine.is_paused()
            engine.step(1.0)
            engine.step(1.0)
            t_paused = engine.state.simulation_time
            val_paused = engine.state.latency_ms

            # Resume
            engine.resume()
            engine.step(1.0)
            t_resumed = engine.state.simulation_time

            passed = (
                t_paused == t_before
                and val_paused == val_before
                and not engine.is_paused()
                and t_resumed > t_paused
            )
            self._record_result(
                "pause() and resume() toggle time advancement",
                passed,
                f"Time before pause={t_before}s, during pause={t_paused}s, resumed={t_resumed}s",
            )
        except Exception as e:
            self._record_result("pause() and resume() toggle time advancement", False, str(e))

        # Test 10: Metric clamping respects physical/domain bounds
        try:
            extreme_tests = [
                ("latency_ms", -50.0, 1.0),
                ("latency_ms", 5000.0, 1000.0),
                ("throughput_mbps", -10.0, 0.0),
                ("throughput_mbps", 9999.0, 1200.0),
                ("packet_loss_pct", -5.0, 0.0),
                ("packet_loss_pct", 150.0, 100.0),
                ("signal_strength_dbm", -200.0, -120.0),
                ("signal_strength_dbm", 10.0, -35.0),
                ("handover_success_pct", -1.0, 0.0),
                ("handover_success_pct", 110.0, 100.0),
                ("active_connections", -20, 0),
                ("active_connections", 10000, 5000),
            ]
            all_clamped = True
            for kpi, input_val, expected_clamp in extreme_tests:
                clamped = clamp_kpi_bounds(kpi, input_val)
                if abs(clamped - expected_clamp) > 1e-4:
                    all_clamped = False
                    break
            self._record_result(
                "Metric clamping respects physical bounds",
                all_clamped,
                f"Tested {len(extreme_tests)} extreme out-of-bounds KPI inputs; all clamped correctly.",
            )
        except Exception as e:
            self._record_result("Metric clamping respects physical bounds", False, str(e))

        # Test 11: Health score stays in 0-100 range and decreases under degradation
        try:
            engine.reset()
            baseline_score = engine.state.health_score

            engine.apply_scenario("CELL_OVERLOAD", "HIGH")
            for _ in range(25):
                engine.step(1.0)
            degraded_score = engine.state.health_score

            # Test edge bounds
            perfect_score = calculate_health_score(
                {
                    "call_drop_rate_pct": 0.0,
                    "packet_loss_pct": 0.0,
                    "latency_ms": 10.0,
                    "signal_strength_dbm": -50.0,
                    "handover_success_pct": 100.0,
                }
            )
            catastrophic_score = calculate_health_score(
                {
                    "call_drop_rate_pct": 10.0,
                    "packet_loss_pct": 20.0,
                    "latency_ms": 500.0,
                    "signal_strength_dbm": -115.0,
                    "handover_success_pct": 60.0,
                }
            )

            passed = (
                0.0 <= baseline_score <= 100.0
                and 0.0 <= degraded_score <= 100.0
                and degraded_score < baseline_score
                and perfect_score == 100.0
                and catastrophic_score == 0.0
            )
            self._record_result(
                "Health score strictly in [0, 100] and decreases under degradation",
                passed,
                f"Perfect=100.0, Baseline={baseline_score:.1f}, Degraded={degraded_score:.1f}, Catastrophic=0.0",
            )
        except Exception as e:
            self._record_result("Health score in [0, 100] and decreases", False, str(e))

        # Test 12: High-call-drop alert triggers correctly at threshold (> 2.0%)
        try:
            normal_alerts = detect_degradation_alerts({"call_drop_rate_pct": 1.2}, 0.0, DEFAULT_ALERT_THRESHOLDS)
            has_alert_sub = any(a["alert_type"] == "HIGH_CALL_DROP" for a in normal_alerts)

            degraded_alerts = detect_degradation_alerts({"call_drop_rate_pct": 2.5}, 0.0, DEFAULT_ALERT_THRESHOLDS)
            has_alert_super = any(a["alert_type"] == "HIGH_CALL_DROP" for a in degraded_alerts)

            passed = (not has_alert_sub) and has_alert_super
            self._record_result(
                "High-call-drop alert triggers correctly at threshold (> 2.0%)",
                passed,
                f"Call drop 1.2% -> Alert={has_alert_sub}, Call drop 2.5% -> Alert={has_alert_super}",
            )
        except Exception as e:
            self._record_result("High-call-drop alert triggers correctly", False, str(e))

        # Test 13: Baseline remains immutable across all steps
        try:
            engine.reset()
            original_baseline_copy = copy.deepcopy(engine.state.baseline_values)

            # Apply series of harsh scenarios
            engine.apply_scenario("CONGESTION", "HIGH")
            for _ in range(10):
                engine.step(1.0)
            engine.apply_scenario("SIGNAL_DEGRADATION", "HIGH")
            for _ in range(10):
                engine.step(1.0)
            engine.apply_scenario("CELL_OVERLOAD", "HIGH")
            for _ in range(10):
                engine.step(1.0)

            # Check if baseline_values inside engine was altered
            current_baseline = engine.state.baseline_values
            immutable = all(
                current_baseline[k] == original_baseline_copy[k] for k in original_baseline_copy
            )
            self._record_result(
                "Baseline values remain strictly immutable in memory",
                immutable,
                f"30 continuous degradation steps executed; baseline values remained identical.",
            )
        except Exception as e:
            self._record_result("Baseline values remain immutable", False, str(e))

        # Test 14: Pre- and post-simulation database integrity verification
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
                "Database integrity preserved (3,600 network rows, 7,043 churn rows, integrity=ok)",
                passed,
                f"FACT_NETWORK_KPI={post_db_state['fact_network_kpi_count']} (expected 3600), "
                f"FACT_CUSTOMER_CHURN={post_db_state['fact_customer_churn_count']} (expected 7043), "
                f"PRAGMA integrity_check='{post_db_state['integrity_check']}'",
            )
        except Exception as e:
            self._record_result("Database integrity preserved", False, str(e))

        # Test 15: Event log records state changes, pauses, resets, and alerts
        try:
            engine.reset()
            engine.clear_event_log()

            engine.apply_scenario("CONGESTION", "MEDIUM")
            engine.step(1.0)
            engine.pause()
            engine.resume()
            engine.reset()

            logs = engine.get_event_log()
            event_types = [e["event_type"] for e in logs]

            has_applied = "SCENARIO_APPLIED" in event_types
            has_pause = "SIMULATION_PAUSED" in event_types
            has_resume = "SIMULATION_RESUMED" in event_types
            has_reset = "SIMULATION_RESET" in event_types

            # Verify log entry schema
            all_valid_schema = all(
                "simulation_time" in e and "event_type" in e and "cell_id" in e and "message" in e
                for e in logs
            )

            passed = has_applied and has_pause and has_resume and has_reset and all_valid_schema
            self._record_result(
                "Event log records state transitions with valid schema",
                passed,
                f"Logged {len(logs)} events; Captured events: {set(event_types)}",
            )
        except Exception as e:
            self._record_result("Event log records transitions", False, str(e))

        # Test 16: Comparison helper returns correct absolute and percentage deltas
        try:
            engine.reset()
            engine.apply_scenario("CONGESTION", "LOW")
            for _ in range(10):
                engine.step(1.0)

            comps = engine.get_comparison()
            valid_deltas = True
            for c in comps:
                expected_abs = round(c["simulated"] - c["baseline"], 3)
                if abs(c["absolute_difference"] - expected_abs) > 1e-3:
                    valid_deltas = False
                    break
                if c["baseline"] != 0:
                    expected_pct = round((expected_abs / abs(c["baseline"])) * 100.0, 2)
                    if abs(c["percentage_difference"] - expected_pct) > 1e-2:
                        valid_deltas = False
                        break

            passed = valid_deltas and len(comps) == len(KPI_KEYS)
            self._record_result(
                "Comparison delta helper returns correct absolute and percentage deltas",
                passed,
                f"Verified {len(comps)} KPI comparisons with formula: abs=sim-base, pct=(abs/base)*100",
            )
        except Exception as e:
            self._record_result("Comparison delta helper calculation", False, str(e))

        # Test 17: Deterministic behavior
        try:
            t1 = calculate_scenario_target(engine.state.baseline_values, "CONGESTION", "MEDIUM")
            t2 = calculate_scenario_target(engine.state.baseline_values, "CONGESTION", "MEDIUM")
            identical = all(t1[k] == t2[k] for k in KPI_KEYS)
            self._record_result(
                "Deterministic behavior (reproducible mathematical targets)",
                identical,
                f"Target calculations identical across repeated invocations.",
            )
        except Exception as e:
            self._record_result("Deterministic behavior", False, str(e))

        # Test 18: Edge case handling
        try:
            invalid_scen_caught = False
            try:
                engine.apply_scenario("ALIEN_ATTACK", "LOW")
            except ValueError:
                invalid_scen_caught = True

            invalid_sev_caught = False
            try:
                engine.apply_scenario("CONGESTION", "ULTRA_EXTREME")
            except ValueError:
                invalid_sev_caught = True

            invalid_cell_caught = False
            try:
                engine.load_cell_baseline("Cell_999999")
            except ValueError:
                invalid_cell_caught = True

            passed = invalid_scen_caught and invalid_sev_caught and invalid_cell_caught
            self._record_result(
                "Edge case handling (invalid scenario, severity, and non-existent cell)",
                passed,
                f"Caught invalid scenario={invalid_scen_caught}, invalid severity={invalid_sev_caught}, invalid cell={invalid_cell_caught}",
            )
        except Exception as e:
            self._record_result("Edge case handling", False, str(e))

        print("\n" + "-" * 80)
        print(f"  RESULTS: {self.tests_passed}/{self.tests_executed} checks passed.")
        if self.tests_failed > 0:
            print(f"  FAILURES ({self.tests_failed}):")
            for f in self.failures:
                print(f"    - {f}")
        print("-" * 80)
        return self.tests_failed == 0


def run_demo():
    """Runs a complete interactive demonstration of the Telecom Simulation Engine."""
    print("\n" + "=" * 80)
    print("  TELECOM NETWORK SIMULATION ENGINE DEMONSTRATION")
    print("=" * 80)

    engine = SimulationEngine(default_cell_id="Cell_0025")
    state = engine.state

    print(f"\n[DEMO STEP 1] Initialized Baseline Cell:")
    print(f"  Cell ID:    {state.cell_id}")
    print(f"  Region:     {state.region}")
    print(f"  Technology: {state.technology}")
    print(f"  Timestamp:  {state.timestamp}")
    print(f"  Baseline Health Score: {state.health_score:.1f} / 100.0")

    print("\n  Baseline KPI Telemetry:")
    for kpi in KPI_KEYS:
        val = state.baseline_values[kpi]
        name = KPI_DISPLAY_NAMES[kpi]
        print(f"    - {name:<26}: {val}")

    # Demo Step 2: Apply Scenarios sequentially
    scenarios_to_demo = [
        ("NORMAL", "LOW", 3),
        ("CONGESTION", "LOW", 10),
        ("CONGESTION", "MEDIUM", 10),
        ("CONGESTION", "HIGH", 10),
        ("SIGNAL_DEGRADATION", "MEDIUM", 10),
        ("CELL_OVERLOAD", "HIGH", 12),
        ("RECOVERY", "HIGH", 15),
    ]

    for scen, sev, steps in scenarios_to_demo:
        print("\n" + "-" * 80)
        print(f"[DEMO] Applying Scenario: '{scen}' | Severity: '{sev}' (Running {steps} steps)")
        print("-" * 80)

        engine.apply_scenario(scen, sev)
        for _ in range(steps):
            engine.step(1.0)

        st = engine.state
        print(f"  Elapsed Simulation Time: {st.simulation_time:.1f}s")
        print(f"  Simulation Health Score: {st.health_score:.1f} / 100.0")
        print(f"  Active Degradation Alerts ({len(st.alerts)}):")
        if st.alerts:
            for a in st.alerts:
                print(f"    * [{a['alert_type']}] (Severity: {a['severity']}) {a['message']}")
        else:
            print("    * None (All telemetry within nominal operating thresholds)")

        print("\n  KPI Comparison Table (Baseline vs Simulated):")
        print(f"    {'Metric':<25} | {'Baseline':<10} | {'Simulated':<10} | {'Abs Diff':<10} | {'% Diff':<10}")
        print(f"    {'-'*25}-|-{'-'*10}-|-{'-'*10}-|-{'-'*10}-|-{'-'*10}")
        for c in engine.get_comparison():
            print(
                f"    {c['metric_name']:<25} | {c['baseline']:<10} | {c['simulated']:<10} | "
                f"{c['absolute_difference']:<10} | {c['percentage_difference']:<+9.2f}%"
            )

    # Demo Step 3: Comparative Scenario Matrix
    print("\n" + "=" * 80)
    print("  MULTI-SCENARIO EVALUATION MATRIX (Cell_0025 at MEDIUM Severity)")
    print("=" * 80)
    matrix = engine.evaluate_all_scenarios(severity="MEDIUM")
    print(f"  {'Scenario':<20} | {'Health':<8} | {'Latency':<9} | {'Tput(Mbps)':<11} | {'Loss(%)':<9} | {'Drop(%)':<9} | {'Conns':<6} | {'Alerts':<6}")
    print(f"  {'-'*20}-|-{'-'*8}-|-{'-'*9}-|-{'-'*11}-|-{'-'*9}-|-{'-'*9}-|-{'-'*6}-|-{'-'*6}")
    for row in matrix:
        print(
            f"  {row['scenario']:<20} | {row['health_score']:<8.1f} | {row['latency_ms']:<9.2f} | "
            f"{row['throughput_mbps']:<11.2f} | {row['packet_loss_pct']:<9.3f} | {row['call_drop_rate_pct']:<9.3f} | "
            f"{row['active_connections']:<6} | {row['active_alerts_count']:<6}"
        )

    # Demo Step 4: Event Log
    print("\n" + "=" * 80)
    print("  SIMULATION EVENT LOG AUDIT TRAIL (Last 8 events)")
    print("=" * 80)
    logs = engine.get_event_log()[-8:]
    for e in logs:
        print(f"  [{e['simulation_time']:>5.1f}s] [{e['event_type']:<18}] {e['message']}")

    # Demo Step 5: Reset verification
    print("\n" + "-" * 80)
    print("[DEMO] Resetting Engine to Pristine Warehouse Baseline...")
    engine.reset()
    print(f"  Reset State Health Score: {engine.state.health_score:.1f} / 100.0")
    print(f"  Simulation Time: {engine.state.simulation_time}s")
    print(f"  Active Alerts: {len(engine.state.alerts)}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    runner = SimulationTestRunner()
    success = runner.run_all_tests()
    if success:
        run_demo()
        sys.exit(0)
    else:
        sys.exit(1)
