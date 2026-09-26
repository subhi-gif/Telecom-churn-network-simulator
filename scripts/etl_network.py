"""
ETL Network Module
Extracts, cleans, transforms, and loads Network KPI Telemetry data
into Mart 2 (Network Performance Star Schema) in SQLite.
"""

import os
import sqlite3
import pandas as pd


def run_network_etl(conn, csv_path=None):
    """
    Executes the Network KPI ETL pipeline.
    
    Parameters:
        conn (sqlite3.Connection): Active SQLite connection with foreign keys enabled.
        csv_path (str, optional): Path to source network CSV.
        
    Returns:
        dict: Detailed execution audit metrics.
    """
    if csv_path is None:
        csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "network_kpi_data.csv")
        
    print("\n" + "=" * 60)
    print("NETWORK PERFORMANCE KPI ETL PIPELINE")
    print("=" * 60)
    
    # -------------------------------------------------------------------------
    # 1. EXTRACT
    # -------------------------------------------------------------------------
    print(f"[EXTRACT] Reading source CSV: {csv_path}")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Source file not found at: {csv_path}")
        
    df_raw = pd.read_csv(csv_path)
    source_row_count = len(df_raw)
    print(f"[EXTRACT] Source rows extracted: {source_row_count}")

    # -------------------------------------------------------------------------
    # 2. STAGING & DATA QUALITY AUDIT
    # -------------------------------------------------------------------------
    print("[STAGING] Running Data Quality validation...")
    df_staging = df_raw.copy()
    
    # Expected exact columns check
    expected_cols = [
        "timestamp", "cell_id", "region", "technology", "latency_ms",
        "throughput_mbps", "packet_loss_pct", "call_drop_rate_pct",
        "signal_strength_dbm", "handover_success_pct", "active_connections"
    ]
    missing_cols = set(expected_cols) - set(df_staging.columns)
    if missing_cols:
        raise ValueError(f"Data Quality Failure: Missing expected columns: {missing_cols}")
        
    # Check nulls
    null_counts = df_staging[expected_cols].isnull().sum().to_dict()
    total_nulls = sum(null_counts.values())
    if total_nulls > 0:
        raise ValueError(f"Data Quality Failure: Null values found in network data: {null_counts}")
    print(f"[STAGING] Null check: 0 nulls across all {len(expected_cols)} columns (Pass)")
    
    # Validate composite natural key (cell_id + timestamp)
    duplicates = df_staging.duplicated(subset=["cell_id", "timestamp"]).sum()
    if duplicates > 0:
        raise ValueError(f"Data Quality Failure: Found {duplicates} duplicate (cell_id, timestamp) rows!")
    print(f"[STAGING] Composite key duplicates: {duplicates} (Pass)")

    # -------------------------------------------------------------------------
    # 3. TRANSFORM & TIME DECOMPOSITION
    # -------------------------------------------------------------------------
    print("[TRANSFORM] Parsing timestamps and decomposing time attributes...")
    # Strip whitespace on text columns
    for col in ["cell_id", "region", "technology", "timestamp"]:
        df_staging[col] = df_staging[col].astype(str).str.strip()
        
    df_staging["dt"] = pd.to_datetime(df_staging["timestamp"])
    df_staging["date"] = df_staging["dt"].dt.strftime("%Y-%m-%d")
    df_staging["year"] = df_staging["dt"].dt.year
    df_staging["quarter"] = df_staging["dt"].dt.quarter
    df_staging["month"] = df_staging["dt"].dt.month
    df_staging["day"] = df_staging["dt"].dt.day
    df_staging["hour"] = df_staging["dt"].dt.hour
    df_staging["minute"] = df_staging["dt"].dt.minute

    # Validate categorical domains
    valid_regions = {"Central", "East", "North", "South", "West"}
    actual_regions = set(df_staging["region"].unique())
    if not actual_regions.issubset(valid_regions):
        raise ValueError(f"Invalid region found: {actual_regions - valid_regions}")
        
    valid_tech = {"LTE", "5G"}
    actual_tech = set(df_staging["technology"].unique())
    if not actual_tech.issubset(valid_tech):
        raise ValueError(f"Invalid technology found: {actual_tech - valid_tech}")

    accepted_row_count = len(df_staging)
    rejected_row_count = source_row_count - accepted_row_count
    print(f"[TRANSFORM] Accepted rows: {accepted_row_count}, Rejected rows: {rejected_row_count}")

    # -------------------------------------------------------------------------
    # 4. DIMENSION LOAD: DIM_CELL
    # -------------------------------------------------------------------------
    print("[LOAD DIMENSIONS] Populating DIM_CELL...")
    cursor = conn.cursor()
    unique_cells = df_staging[["cell_id"]].drop_duplicates().sort_values("cell_id").values.tolist()
    cursor.executemany("INSERT OR IGNORE INTO DIM_CELL (cell_id) VALUES (?);", unique_cells)
    conn.commit()
    
    cursor.execute("SELECT cell_id, cell_key FROM DIM_CELL;")
    cell_key_map = dict(cursor.fetchall())
    print(f"[LOAD DIMENSIONS] Loaded {len(cell_key_map)} unique cells into DIM_CELL.")

    # -------------------------------------------------------------------------
    # 5. DIMENSION LOAD: DIM_REGION
    # -------------------------------------------------------------------------
    print("[LOAD DIMENSIONS] Populating DIM_REGION...")
    unique_regions = df_staging[["region"]].drop_duplicates().sort_values("region").values.tolist()
    cursor.executemany("INSERT OR IGNORE INTO DIM_REGION (region_name) VALUES (?);", unique_regions)
    conn.commit()
    
    cursor.execute("SELECT region_name, region_key FROM DIM_REGION;")
    region_key_map = dict(cursor.fetchall())
    print(f"[LOAD DIMENSIONS] Loaded {len(region_key_map)} unique regions into DIM_REGION.")

    # -------------------------------------------------------------------------
    # 6. DIMENSION LOAD: DIM_NETWORK_TECH
    # -------------------------------------------------------------------------
    print("[LOAD DIMENSIONS] Populating DIM_NETWORK_TECH...")
    unique_tech = df_staging[["technology"]].drop_duplicates().sort_values("technology").values.tolist()
    cursor.executemany("INSERT OR IGNORE INTO DIM_NETWORK_TECH (technology_name) VALUES (?);", unique_tech)
    conn.commit()
    
    cursor.execute("SELECT technology_name, technology_key FROM DIM_NETWORK_TECH;")
    tech_key_map = dict(cursor.fetchall())
    print(f"[LOAD DIMENSIONS] Loaded {len(tech_key_map)} unique technologies into DIM_NETWORK_TECH.")

    # -------------------------------------------------------------------------
    # 7. DIMENSION LOAD: DIM_TIME
    # -------------------------------------------------------------------------
    print("[LOAD DIMENSIONS] Populating DIM_TIME...")
    time_cols = ["timestamp", "date", "hour", "minute", "day", "month", "quarter", "year"]
    unique_times = df_staging[time_cols].drop_duplicates().sort_values("timestamp").values.tolist()
    cursor.executemany(f"""
        INSERT OR IGNORE INTO DIM_TIME ({', '.join(time_cols)})
        VALUES ({', '.join(['?'] * len(time_cols))});
    """, unique_times)
    conn.commit()
    
    cursor.execute("SELECT timestamp, time_key FROM DIM_TIME;")
    time_key_map = dict(cursor.fetchall())
    print(f"[LOAD DIMENSIONS] Loaded {len(time_key_map)} discrete minute time slices into DIM_TIME.")

    # -------------------------------------------------------------------------
    # 8. FACT LOAD: FACT_NETWORK_KPI
    # -------------------------------------------------------------------------
    print("[LOAD FACT] Resolving foreign keys and populating FACT_NETWORK_KPI...")
    df_staging["cell_key"] = df_staging["cell_id"].map(cell_key_map)
    df_staging["region_key"] = df_staging["region"].map(region_key_map)
    df_staging["technology_key"] = df_staging["technology"].map(tech_key_map)
    df_staging["time_key"] = df_staging["timestamp"].map(time_key_map)

    # Validate unresolved keys
    for key_col in ["cell_key", "region_key", "technology_key", "time_key"]:
        unresolved = df_staging[key_col].isnull().sum()
        if unresolved > 0:
            raise ValueError(f"Foreign Key Resolution Failure: {unresolved} unresolved {key_col} values!")

    fact_cols = [
        "cell_key", "region_key", "technology_key", "time_key",
        "latency_ms", "throughput_mbps", "packet_loss_pct", "call_drop_rate_pct",
        "signal_strength_dbm", "handover_success_pct", "active_connections"
    ]
    fact_records = df_staging[fact_cols].values.tolist()

    cursor.executemany(f"""
        INSERT INTO FACT_NETWORK_KPI (
            {', '.join(fact_cols)}, reading_count
        ) VALUES ({', '.join(['?'] * len(fact_cols))}, 1);
    """, fact_records)
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM FACT_NETWORK_KPI;")
    final_fact_count = cursor.fetchone()[0]
    print(f"[LOAD FACT] Loaded {final_fact_count} rows into FACT_NETWORK_KPI.")

    audit = {
        "source_rows": source_row_count,
        "staging_rows": len(df_staging),
        "accepted_rows": accepted_row_count,
        "rejected_rows": rejected_row_count,
        "dim_cell_rows": len(cell_key_map),
        "dim_region_rows": len(region_key_map),
        "dim_tech_rows": len(tech_key_map),
        "dim_time_rows": len(time_key_map),
        "fact_network_kpi_rows": final_fact_count
    }

    print("[NETWORK ETL] Complete successfully!")
    return audit


if __name__ == "__main__":
    db_file = os.path.join(os.path.dirname(__file__), "..", "database", "warehouse.db")
    connection = sqlite3.connect(db_file)
    connection.execute("PRAGMA foreign_keys = ON;")
    run_network_etl(connection)
    connection.close()
