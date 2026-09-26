"""
Customer Service Pattern Mining & Association Rules Module
Implements an Apriori association analysis engine to discover service subscription patterns
correlated with customer churn (targeting Churn=Yes).
Computes Support, Confidence, and Lift without external library dependencies.
"""

from collections import defaultdict
from itertools import combinations
import os
import sqlite3
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple, Union

import pandas as pd

from backend.mining.preprocessing import RESULTS_DIR
from backend.olap.queries import get_connection


class CustomerAssociationMiner:
    """
    Market basket / association rule mining engine for customer service profiles.
    Discovers multi-service subscription patterns associated with customer churn.
    """

    def __init__(
        self,
        min_support: float = 0.05,
        min_confidence: float = 0.35,
        min_lift: float = 1.20,
        target_consequent: Optional[str] = "Churn=Yes",
        max_itemset_len: int = 3,
    ):
        self.min_support = min_support
        self.min_confidence = min_confidence
        self.min_lift = min_lift
        self.target_consequent = target_consequent
        self.max_itemset_len = max_itemset_len

        self.transactions: List[FrozenSet[str]] = []
        self.frequent_itemsets: Dict[FrozenSet[str], float] = {}
        self.rules_df: Optional[pd.DataFrame] = None
        self.dataset_size: int = 0

    def load_transactions(
        self,
        conn_or_path: Union[sqlite3.Connection, str, None] = None,
    ) -> List[FrozenSet[str]]:
        """
        Extracts categorical service attributes and churn flag from warehouse.db.
        Builds discrete item transactions for every customer record.
        Strictly excludes customerID and continuous monetary values.
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
                    p.Contract,
                    p.InternetService,
                    p.PhoneService,
                    p.MultipleLines,
                    p.OnlineSecurity,
                    p.OnlineBackup,
                    p.DeviceProtection,
                    p.TechSupport,
                    p.StreamingTV,
                    p.StreamingMovies,
                    p.PaperlessBilling,
                    p.PaymentMethod,
                    CASE WHEN f.churn_flag = 1 THEN 'Yes' ELSE 'No' END AS Churn
                FROM FACT_CUSTOMER_CHURN f
                JOIN DIM_PLAN p ON f.plan_key = p.plan_key;
            """
            df = pd.read_sql_query(sql, conn)
        finally:
            if owns_conn:
                conn.close()

        self.dataset_size = len(df)
        transactions = []
        for _, row in df.iterrows():
            itemset = frozenset(f"{col}={row[col]}" for col in df.columns)
            transactions.append(itemset)

        self.transactions = transactions
        return self.transactions

    def find_frequent_itemsets(self) -> Dict[FrozenSet[str], float]:
        """
        Executes Apriori itemset generation up to max_itemset_len
        meeting the minimum support threshold.
        """
        if not self.transactions:
            self.load_transactions()

        N = self.dataset_size
        freq_itemsets: Dict[FrozenSet[str], float] = {}

        # 1. Frequent 1-itemsets
        c1 = defaultdict(int)
        for t in self.transactions:
            for item in t:
                c1[frozenset([item])] += 1

        l1 = {itemset: cnt / N for itemset, cnt in c1.items() if (cnt / N) >= self.min_support}
        freq_itemsets.update(l1)

        current_l = l1
        k = 2

        while k <= self.max_itemset_len and current_l:
            # Candidate generation: join L_{k-1} with L_{k-1}
            prev_itemsets = list(current_l.keys())
            candidates: Set[FrozenSet[str]] = set()

            for i in range(len(prev_itemsets)):
                for j in range(i + 1, len(prev_itemsets)):
                    union_set = prev_itemsets[i] | prev_itemsets[j]
                    if len(union_set) == k:
                        candidates.add(union_set)

            # Count support for candidates
            ck_counts = defaultdict(int)
            for t in self.transactions:
                for cand in candidates:
                    if cand.issubset(t):
                        ck_counts[cand] += 1

            current_l = {
                itemset: cnt / N
                for itemset, cnt in ck_counts.items()
                if (cnt / N) >= self.min_support
            }
            freq_itemsets.update(current_l)
            k += 1

        self.frequent_itemsets = freq_itemsets
        return self.frequent_itemsets

    def generate_rules(self) -> pd.DataFrame:
        """
        Generates association rules meeting minimum confidence and minimum lift.
        Filters rules targeting self.target_consequent if specified.
        Eliminates duplicate and trivial rules.
        """
        if not self.frequent_itemsets:
            self.find_frequent_itemsets()

        rules = []

        for itemset, supp_xy in self.frequent_itemsets.items():
            if len(itemset) < 2:
                continue

            # Candidate consequents: single items
            for item in itemset:
                consequent_itemset = frozenset([item])
                antecedent_itemset = itemset - consequent_itemset

                # Check target filter if specified
                if self.target_consequent is not None and item != self.target_consequent:
                    continue

                supp_x = self.frequent_itemsets.get(antecedent_itemset, 0.0)
                supp_y = self.frequent_itemsets.get(consequent_itemset, 0.0)

                if supp_x > 0.0 and supp_y > 0.0:
                    confidence = supp_xy / supp_x
                    lift = confidence / supp_y

                    if confidence >= self.min_confidence and lift >= self.min_lift:
                        antecedent_str = " & ".join(sorted(list(antecedent_itemset)))
                        consequent_str = item

                        rules.append(
                            {
                                "antecedent": antecedent_str,
                                "consequent": consequent_str,
                                "support": round(float(supp_xy), 4),
                                "confidence": round(float(confidence), 4),
                                "lift": round(float(lift), 4),
                                "antecedent_support": round(float(supp_x), 4),
                                "consequent_support": round(float(supp_y), 4),
                            }
                        )

        if not rules:
            self.rules_df = pd.DataFrame(
                columns=[
                    "antecedent",
                    "consequent",
                    "support",
                    "confidence",
                    "lift",
                    "antecedent_support",
                    "consequent_support",
                ]
            )
        else:
            df_rules = pd.DataFrame(rules)
            # Remove duplicate rules
            df_rules = df_rules.drop_duplicates(subset=["antecedent", "consequent"])
            # Rank primarily by Lift (correlation strength), then Confidence
            df_rules = df_rules.sort_values(by=["lift", "confidence"], ascending=[False, False]).reset_index(drop=True)
            self.rules_df = df_rules

        return self.rules_df

    def save_results(self) -> str:
        """Exports association rules to backend/mining/results/association_rules.csv."""
        if self.rules_df is None:
            self.generate_rules()

        csv_path = os.path.join(RESULTS_DIR, "association_rules.csv")
        self.rules_df.to_csv(csv_path, index=False)
        return csv_path


def run_association_mining_pipeline(
    conn_or_path: Any = None,
    min_support: float = 0.05,
    min_confidence: float = 0.35,
    min_lift: float = 1.20,
    target_consequent: Optional[str] = "Churn=Yes",
) -> Dict[str, Any]:
    """Convenience runner function for Customer Service Pattern Mining pipeline."""
    miner = CustomerAssociationMiner(
        min_support=min_support,
        min_confidence=min_confidence,
        min_lift=min_lift,
        target_consequent=target_consequent,
    )
    miner.load_transactions(conn_or_path)
    miner.find_frequent_itemsets()
    rules = miner.generate_rules()
    csv_path = miner.save_results()

    return {
        "transactions_count": miner.dataset_size,
        "frequent_itemsets_count": len(miner.frequent_itemsets),
        "rules_count": len(rules),
        "target_consequent": target_consequent,
        "top_rules": rules.head(10).to_dict(orient="records"),
        "results_csv": csv_path,
    }
