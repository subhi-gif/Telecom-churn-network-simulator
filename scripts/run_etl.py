"""
Master ETL Pipeline Runner & Validation Suite
Orchestrates end-to-end extraction, transformation, loading, and validation
for both Customer Churn and Network Performance Data Marts.
"""

import os
import sys
import argparse
import sqlite3
import pandas as pd
import numpy as np

# Add scripts directory to path if run directly
sys.path.append(os.path.dirname(__file__))

from etl_customer import run_customer_etl
from etl_network import run_network_etl


def reset_database(conn, schema_path):
    """Rebuilds the entire database schema from schema.sql."""
    print("\n" + "=" * 60)
    print("DATABASE SCHEMA RESET")
    print("=" * 60)
    print(f"Executing DDL from: {schema_path}")
    
    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"Schema file not found at: {schema_path}")
        
    with open(schema_path, "r", encoding="utf-8") as f:
        ddl_script = f.read()
        
    conn.executescript(ddl_script)
    conn.commit()
    print("Database schema successfully recreated from schema.sql.")


def run_validation_suite(conn, customer_csv_path, network_csv_path):
    """
    Executes post-ETL data integrity and aggregate reconciliation checks.
    """
    print("\n" + "=" * 60)
    print("POST-ETL DATA VALIDATION & RECONCILIATION SUITE")
    print("=" * 60)
    
    cursor = conn.cursor()
    validation_results = {}
    
    # 1. SQLite Integrity Check
    cursor.execute("PRAGMA integrity_check;")
    integrity = cursor.fetchall()
    integrity_status = "PASS" if integrity == [("ok",)] else "FAIL"
    print(f"[CHECK 1] PRAGMA integrity_check: {integrity} -> {integrity_status}")
    validation_results["integrity_check"] = integrity_status

    # 2. Foreign Key Integrity Check
    cursor.execute("PRAGMA foreign_key_check;")
    fk_violations = cursor.fetchall()
    fk_status = "PASS (0 violations)" if len(fk_violations) == 0 else f"FAIL ({len(fk_violations)} violations)"
    print(f"[CHECK 2] Foreign Key Integrity: {fk_status}")
    validation_results["foreign_key_check"] = fk_status

    # 3. Duplicate Business Keys Check
    cursor.execute("SELECT customerID, COUNT(*) FROM DIM_CUSTOMER GROUP BY customerID HAVING COUNT(*) > 1;")
    dup_cust = cursor.fetchall()
    cursor.execute("SELECT cell_id, COUNT(*) FROM DIM_CELL GROUP BY cell_id HAVING COUNT(*) > 1;")
    dup_cell = cursor.fetchall()
    cursor.execute("SELECT timestamp, COUNT(*) FROM DIM_TIME GROUP BY timestamp HAVING COUNT(*) > 1;")
    dup_time = cursor.fetchall()
    
    dup_status = "PASS (0 duplicates)" if (len(dup_cust) == 0 and len(dup_cell) == 0 and len(dup_time) == 0) else "FAIL"
    print(f"[CHECK 3] Business Key Uniqueness (customerID, cell_id, timestamp): {dup_status}")
    validation_results["business_key_duplicates"] = dup_status

    # 4. Row Count Reconciliation (Customer)
    df_raw_cust = pd.read_csv(customer_csv_path, dtype=str)
    source_cust_count = len(df_raw_cust)
    cursor.execute("SELECT COUNT(*) FROM FACT_CUSTOMER_CHURN;")
    fact_cust_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM DIM_CUSTOMER;")
    dim_cust_count = cursor.fetchone()[0]
    
    cust_row_recon = "PASS" if (source_cust_count == fact_cust_count == dim_cust_count) else "FAIL"
    print(f"[CHECK 4] Customer Row Reconciliation: Source={source_cust_count} | Dim={dim_cust_count} | Fact={fact_cust_count} -> {cust_row_recon}")
    validation_results["customer_row_recon"] = cust_row_recon

    # 5. Row Count Reconciliation (Network)
    df_raw_net = pd.read_csv(network_csv_path)
    source_net_count = len(df_raw_net)
    cursor.execute("SELECT COUNT(*) FROM FACT_NETWORK_KPI;")
    fact_net_count = cursor.fetchone()[0]
    
    net_row_recon = "PASS" if (source_net_count == fact_net_count) else "FAIL"
    print(f"[CHECK 5] Network Row Reconciliation: Source={source_net_count} | Fact={fact_net_count} -> {net_row_recon}")
    validation_results["network_row_recon"] = net_row_recon

    # 6. Customer Analytical Aggregates Reconciliation
    # Raw source calculations
    df_raw_cust["TotalCharges_num"] = pd.to_numeric(df_raw_cust["TotalCharges"].str.strip(), errors="coerce").fillna(0.0)
    df_raw_cust["MonthlyCharges_num"] = pd.to_numeric(df_raw_cust["MonthlyCharges"].str.strip(), errors="coerce")
    source_churn_count = (df_raw_cust["Churn"].str.strip() == "Yes").sum()
    source_non_churn_count = (df_raw_cust["Churn"].str.strip() == "No").sum()
    source_avg_monthly = df_raw_cust["MonthlyCharges_num"].mean()
    source_total_charges = df_raw_cust["TotalCharges_num"].sum()

    # Warehouse calculations
    cursor.execute("""
        SELECT 
            COUNT(*) AS total_customers,
            SUM(churn_flag) AS churned_customers,
            SUM(CASE WHEN churn_flag = 0 THEN 1 ELSE 0 END) AS non_churned_customers,
            AVG(monthly_charges) AS avg_monthly_charges,
            SUM(total_charges) AS sum_total_charges
        FROM FACT_CUSTOMER_CHURN;
    """)
    wh_cust = cursor.fetchone()
    wh_total_cust, wh_churn_cnt, wh_non_churn_cnt, wh_avg_monthly, wh_sum_total = wh_cust

    print("\n--- CUSTOMER AGGREGATE RECONCILIATION ---")
    print(f"Total Customers: Source={source_cust_count} | Warehouse={wh_total_cust} | Match: {source_cust_count == wh_total_cust}")
    print(f"Churned Customers: Source={source_churn_count} | Warehouse={wh_churn_cnt} | Match: {source_churn_count == wh_churn_cnt}")
    print(f"Non-Churned Customers: Source={source_non_churn_count} | Warehouse={wh_non_churn_cnt} | Match: {source_non_churn_count == wh_non_churn_cnt}")
    print(f"Avg Monthly Charges: Source=${source_avg_monthly:.4f} | Warehouse=${wh_avg_monthly:.4f} | Diff: {abs(source_avg_monthly - wh_avg_monthly):.6f}")
    print(f"Total Charges Sum: Source=${source_total_charges:.2f} | Warehouse=${wh_sum_total:.2f} | Diff: {abs(source_total_charges - wh_sum_total):.4f}")

    # 7. Network Analytical Aggregates Reconciliation
    # Raw source calculations
    src_net_avg_lat = df_raw_net["latency_ms"].mean()
    src_net_avg_tput = df_raw_net["throughput_mbps"].mean()
    src_net_avg_ploss = df_raw_net["packet_loss_pct"].mean()
    src_net_avg_cdr = df_raw_net["call_drop_rate_pct"].mean()
    src_net_avg_conn = df_raw_net["active_connections"].mean()

    # Warehouse calculations
    cursor.execute("""
        SELECT
            AVG(latency_ms),
            AVG(throughput_mbps),
            AVG(packet_loss_pct),
            AVG(call_drop_rate_pct),
            AVG(active_connections)
        FROM FACT_NETWORK_KPI;
    """)
    wh_net = cursor.fetchone()
    wh_net_avg_lat, wh_net_avg_tput, wh_net_avg_ploss, wh_net_avg_cdr, wh_net_avg_conn = wh_net

    print("\n--- NETWORK AGGREGATE RECONCILIATION ---")
    print(f"Avg Latency (ms): Source={src_net_avg_lat:.4f} | Warehouse={wh_net_avg_lat:.4f} | Diff: {abs(src_net_avg_lat - wh_net_avg_lat):.6f}")
    print(f"Avg Throughput (Mbps): Source={src_net_avg_tput:.4f} | Warehouse={wh_net_avg_tput:.4f} | Diff: {abs(src_net_avg_tput - wh_net_avg_tput):.6f}")
    print(f"Avg Packet Loss (%): Source={src_net_avg_ploss:.4f} | Warehouse={wh_net_avg_ploss:.4f} | Diff: {abs(src_net_avg_ploss - wh_net_avg_ploss):.6f}")
    print(f"Avg Call Drop Rate (%): Source={src_net_avg_cdr:.4f} | Warehouse={wh_net_avg_cdr:.4f} | Diff: {abs(src_net_avg_cdr - wh_net_avg_cdr):.6f}")
    print(f"Avg Active Connections: Source={src_net_avg_conn:.4f} | Warehouse={wh_net_avg_conn:.4f} | Diff: {abs(src_net_avg_conn - wh_net_avg_conn):.6f}")

    return {
        "validation_results": validation_results,
        "customer_aggregates": {
            "total_customers": wh_total_cust,
            "churned": wh_churn_cnt,
            "non_churned": wh_non_churn_cnt,
            "churn_rate_pct": (wh_churn_cnt / wh_total_cust) * 100,
            "avg_monthly_charges": wh_avg_monthly,
            "sum_total_charges": wh_sum_total
        },
        "network_aggregates": {
            "total_observations": fact_net_count,
            "avg_latency_ms": wh_net_avg_lat,
            "avg_throughput_mbps": wh_net_avg_tput,
            "avg_packet_loss_pct": wh_net_avg_ploss,
            "avg_call_drop_rate_pct": wh_net_avg_cdr,
            "avg_active_connections": wh_net_avg_conn
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Telecom DWDM ETL Master Pipeline")
    parser.add_argument("--reset", action="store_true", help="Recreate warehouse schema from schema.sql before loading")
    args = parser.parse_args()

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    db_path = os.path.join(project_root, "database", "warehouse.db")
    schema_path = os.path.join(project_root, "database", "schema.sql")
    customer_csv = os.path.join(project_root, "data", "WA_Fn-UseC_-Telco-Customer-Churn.csv")
    network_csv = os.path.join(project_root, "data", "network_kpi_data.csv")

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")

    if args.reset:
        reset_database(conn, schema_path)

    # Execute Customer ETL
    cust_audit = run_customer_etl(conn, customer_csv)

    # Execute Network ETL
    net_audit = run_network_etl(conn, network_csv)

    # Execute Validation Suite
    val_report = run_validation_suite(conn, customer_csv, network_csv)

    conn.close()

    print("\n" + "=" * 60)
    print("ETL PIPELINE EXECUTION SUMMARY")
    print("=" * 60)
    print(f"Customer Source Rows: {cust_audit['source_rows']} | Loaded Fact Rows: {cust_audit['fact_customer_churn_rows']}")
    print(f"Network Source Rows:  {net_audit['source_rows']}  | Loaded Fact Rows: {net_audit['fact_network_kpi_rows']}")
    print(f"Data Quality Cleaned: {cust_audit['blank_total_charges_cleaned']} TotalCharges blanks imputed to 0.00")
    print(f"Integrity Check:      {val_report['validation_results']['integrity_check']}")
    print(f"Foreign Key Check:    {val_report['validation_results']['foreign_key_check']}")
    print("Pipeline completed successfully without errors!")


if __name__ == "__main__":
    main()
