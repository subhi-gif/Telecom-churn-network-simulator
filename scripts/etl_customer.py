"""
ETL Customer Module
Extracts, cleans, transforms, and loads IBM Telco Customer Churn data
into Mart 1 (Customer Churn Star Schema) in SQLite.
"""

import os
import sqlite3
import pandas as pd
import numpy as np


def run_customer_etl(conn, csv_path=None):
    """
    Executes the Customer Churn ETL pipeline.
    
    Parameters:
        conn (sqlite3.Connection): Active SQLite connection with foreign keys enabled.
        csv_path (str, optional): Path to source customer CSV.
        
    Returns:
        dict: Detailed execution audit metrics.
    """
    if csv_path is None:
        csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "WA_Fn-UseC_-Telco-Customer-Churn.csv")
    
    print("\n" + "=" * 60)
    print("CUSTOMER CHURN ETL PIPELINE")
    print("=" * 60)
    
    # -------------------------------------------------------------------------
    # 1. EXTRACT
    # -------------------------------------------------------------------------
    print(f"[EXTRACT] Reading source CSV: {csv_path}")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Source file not found at: {csv_path}")
        
    df_raw = pd.read_csv(csv_path, dtype=str)
    source_row_count = len(df_raw)
    print(f"[EXTRACT] Source rows extracted: {source_row_count}")

    # -------------------------------------------------------------------------
    # 2. STAGING & DATA QUALITY AUDIT
    # -------------------------------------------------------------------------
    print("[STAGING] Running Data Quality validation...")
    df_staging = df_raw.copy()
    
    # Check duplicate customer IDs
    duplicate_cust_count = df_staging["customerID"].duplicated().sum()
    if duplicate_cust_count > 0:
        raise ValueError(f"Data Quality Failure: Found {duplicate_cust_count} duplicate customerID records!")
    print(f"[STAGING] Duplicate customerID count: {duplicate_cust_count} (Pass)")
    
    # Check whitespace / blanks in TotalCharges
    blank_total_charges_mask = df_staging["TotalCharges"].str.strip() == ""
    blank_total_charges_count = blank_total_charges_mask.sum()
    print(f"[STAGING] Identified {blank_total_charges_count} records with blank/whitespace in TotalCharges.")
    
    # Verify that all blank TotalCharges correspond to tenure == 0
    blank_tenures = df_staging.loc[blank_total_charges_mask, "tenure"].unique()
    print(f"[STAGING] Unique tenure values for blank TotalCharges: {blank_tenures.tolist()}")
    if not (len(blank_tenures) == 1 and str(blank_tenures[0]).strip() == "0"):
        print("[WARNING] Blank TotalCharges exist for accounts with tenure > 0!")

    # -------------------------------------------------------------------------
    # 3. TRANSFORM
    # -------------------------------------------------------------------------
    print("[TRANSFORM] Applying dimensional transformations...")
    
    # Clean text columns (strip whitespace)
    for col in df_staging.select_dtypes(include="object").columns:
        df_staging[col] = df_staging[col].str.strip()
        
    # Transform TotalCharges: replace blanks with '0.00' and cast to float
    df_staging["TotalCharges_cleaned"] = df_staging["TotalCharges"].replace("", "0.00").astype(float)
    df_staging["MonthlyCharges_cleaned"] = df_staging["MonthlyCharges"].astype(float)
    df_staging["tenure_cleaned"] = df_staging["tenure"].astype(int)
    df_staging["SeniorCitizen_cleaned"] = df_staging["SeniorCitizen"].astype(int)

    # Transform Churn: 'Yes' -> 1, 'No' -> 0
    churn_map = {"Yes": 1, "No": 0}
    df_staging["churn_flag"] = df_staging["Churn"].map(churn_map)
    if df_staging["churn_flag"].isnull().sum() > 0:
        raise ValueError("Invalid categorical values found in Churn column!")
        
    # Derive tenure_band for analytical categorization
    def categorize_tenure(t):
        if t <= 12:
            return "0-12 months"
        elif t <= 24:
            return "13-24 months"
        elif t <= 48:
            return "25-48 months"
        else:
            return "49-72 months"
            
    df_staging["tenure_band"] = df_staging["tenure_cleaned"].apply(categorize_tenure)
    print(f"[TRANSFORM] Derived tenure_band distribution:\n{df_staging['tenure_band'].value_counts().to_dict()}")

    accepted_row_count = len(df_staging)
    rejected_row_count = source_row_count - accepted_row_count
    print(f"[TRANSFORM] Accepted rows: {accepted_row_count}, Rejected rows: {rejected_row_count}")

    # -------------------------------------------------------------------------
    # 4. DIMENSION LOAD: DIM_CUSTOMER
    # -------------------------------------------------------------------------
    print("[LOAD DIMENSIONS] Populating DIM_CUSTOMER...")
    cursor = conn.cursor()
    
    customer_dim_records = df_staging[[
        "customerID", "gender", "SeniorCitizen_cleaned", "Partner", "Dependents", "tenure_cleaned"
    ]].values.tolist()
    
    cursor.executemany("""
        INSERT INTO DIM_CUSTOMER (
            customerID, gender, SeniorCitizen, Partner, Dependents, tenure
        ) VALUES (?, ?, ?, ?, ?, ?);
    """, customer_dim_records)
    conn.commit()
    
    # Query customer_key mapping
    cursor.execute("SELECT customerID, customer_key FROM DIM_CUSTOMER;")
    customer_key_map = dict(cursor.fetchall())
    print(f"[LOAD DIMENSIONS] Loaded {len(customer_key_map)} rows into DIM_CUSTOMER.")

    # -------------------------------------------------------------------------
    # 5. DIMENSION LOAD: DIM_PLAN
    # -------------------------------------------------------------------------
    print("[LOAD DIMENSIONS] Populating DIM_PLAN (deduplicating service plans)...")
    plan_cols = [
        "Contract", "PhoneService", "MultipleLines", "InternetService",
        "OnlineSecurity", "OnlineBackup", "DeviceProtection", "TechSupport",
        "StreamingTV", "StreamingMovies", "PaperlessBilling", "PaymentMethod"
    ]
    
    unique_plans = df_staging[plan_cols].drop_duplicates().values.tolist()
    cursor.executemany(f"""
        INSERT OR IGNORE INTO DIM_PLAN (
            {', '.join(plan_cols)}
        ) VALUES ({', '.join(['?'] * len(plan_cols))});
    """, unique_plans)
    conn.commit()
    
    # Query plan_key mapping
    cursor.execute(f"SELECT {', '.join(plan_cols)}, plan_key FROM DIM_PLAN;")
    plan_rows = cursor.fetchall()
    plan_key_map = {tuple(row[:-1]): row[-1] for row in plan_rows}
    print(f"[LOAD DIMENSIONS] Loaded {len(plan_key_map)} distinct service plans into DIM_PLAN.")

    # -------------------------------------------------------------------------
    # 6. FACT LOAD: FACT_CUSTOMER_CHURN
    # -------------------------------------------------------------------------
    print("[LOAD FACT] Resolving foreign keys and populating FACT_CUSTOMER_CHURN...")
    
    # Map foreign keys
    df_staging["customer_key"] = df_staging["customerID"].map(customer_key_map)
    
    plan_tuples = df_staging[plan_cols].apply(tuple, axis=1)
    df_staging["plan_key"] = plan_tuples.map(plan_key_map)
    
    # Check for unresolvable foreign keys
    unresolved_cust = df_staging["customer_key"].isnull().sum()
    unresolved_plan = df_staging["plan_key"].isnull().sum()
    if unresolved_cust > 0 or unresolved_plan > 0:
        raise ValueError(f"Foreign Key Resolution Failure: Unresolved customer keys={unresolved_cust}, plan keys={unresolved_plan}")

    fact_records = df_staging[[
        "customer_key", "plan_key", "MonthlyCharges_cleaned", "TotalCharges_cleaned", "churn_flag"
    ]].values.tolist()

    cursor.executemany("""
        INSERT INTO FACT_CUSTOMER_CHURN (
            customer_key, plan_key, monthly_charges, total_charges, churn_flag, customer_count
        ) VALUES (?, ?, ?, ?, ?, 1);
    """, fact_records)
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM FACT_CUSTOMER_CHURN;")
    final_fact_count = cursor.fetchone()[0]
    print(f"[LOAD FACT] Loaded {final_fact_count} rows into FACT_CUSTOMER_CHURN.")

    # Summary metrics
    audit = {
        "source_rows": source_row_count,
        "staging_rows": len(df_staging),
        "accepted_rows": accepted_row_count,
        "rejected_rows": rejected_row_count,
        "blank_total_charges_cleaned": blank_total_charges_count,
        "dim_customer_rows": len(customer_key_map),
        "dim_plan_rows": len(plan_key_map),
        "fact_customer_churn_rows": final_fact_count
    }
    
    print("[CUSTOMER ETL] Complete successfully!")
    return audit


if __name__ == "__main__":
    db_file = os.path.join(os.path.dirname(__file__), "..", "database", "warehouse.db")
    connection = sqlite3.connect(db_file)
    connection.execute("PRAGMA foreign_keys = ON;")
    run_customer_etl(connection)
    connection.close()
