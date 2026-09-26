# Telecom Data Mining Layer

The Data Mining layer provides advanced machine learning, pattern mining, and unsupervised clustering capabilities over the two decoupled data marts in the SQLite star schema warehouse (`database/warehouse.db`).

---

## Architectural Taxonomy: Three Distinct Analytical Pillars

This project strictly delineates three distinct paradigms of data mining:

```
                                  DATA MINING LAYER
                                          |
       +----------------------------------+----------------------------------+
       |                                  |                                  |
[1. SUPERVISED PREDICTION]     [2. UNSUPERVISED CLUSTERING]      [3. PATTERN / ASSOCIATION]
• Target: Churn Flag (0/1)     • Target: None (Unlabeled)        • Target: Co-occurrence Patterns
• Goal: Predict future loss    • Goal: Discover KPI regimes      • Goal: Find frequent itemsets
• Models: LogReg, DecTree      • Algorithm: K-Means (K=2..5)     • Algorithm: Apriori
• Metric: Recall / ROC-AUC     • Metric: Silhouette / Inertia    • Metric: Support / Conf / Lift
```

> [!IMPORTANT]
> **Strict Non-Causal Standard**: None of the models, feature importances, or association rules make causal claims. Statistical associations indicate that specific conditions or feature values are *"associated with higher or lower predicted churn probabilities"* or *"statistically co-occur with churn events"*, rather than *"causing churn"*.

---

## 1. Churn Prediction Objective

The business goal of customer churn prediction is to identify customer accounts at high risk of cancelling service prior to actual contract termination. Because the cost of acquiring a new subscriber substantially exceeds the cost of proactive retention, the model prioritizes **recall on the positive (churn) class** over raw accuracy.

---

## 2. Features Used

The feature set incorporates 19 attributes extracted from `DIM_CUSTOMER` and `DIM_PLAN`:

### Demographics (4)
- `gender` (Male, Female)
- `SeniorCitizen` (0, 1)
- `Partner` (Yes, No)
- `Dependents` (Yes, No)

### Lifecycle & Billing (5)
- `tenure` (continuous months, standardized)
- `tenure_band` (0-12m, 13-24m, 25-48m, 49-72m)
- `Contract` (Month-to-month, One year, Two year)
- `PaperlessBilling` (Yes, No)
- `PaymentMethod` (Electronic check, Mailed check, Bank transfer, Credit card)

### Services & Subscriptions (8)
- `PhoneService` (Yes, No)
- `MultipleLines` (Yes, No, No phone service)
- `InternetService` (DSL, Fiber optic, No)
- `OnlineSecurity` (Yes, No, No internet service)
- `OnlineBackup` (Yes, No, No internet service)
- `DeviceProtection` (Yes, No, No internet service)
- `TechSupport` (Yes, No, No internet service)
- `StreamingTV` (Yes, No, No internet service)
- `StreamingMovies` (Yes, No, No internet service)

### Financial Measures (2)
- `monthly_charges` (continuous $, standardized)
- `total_charges` (continuous $, standardized)

---

## 3. Features Excluded (Anti-Leakage & Identifier Isolation)

To ensure data integrity, several fields are strictly isolated:
- `customerID`: High-cardinality unique surrogate key with zero generalizable predictive utility.
- `customer_key`, `plan_key`, `customer_churn_key`: Warehouse technical surrogate keys.
- `churn_flag` / `Churn`: The prediction target itself, strictly prevented from appearing in input feature matrices $X_{\text{train}}$ and $X_{\text{test}}$.

---

## 4. Preprocessing Pipeline

1. **Stratified Split**: 80% Training ($N = 5,634$) and 20% Test ($N = 1,409$), stratifying on `churn_flag` to preserve the 26.54% churn class prevalence in both subsets.
2. **Strict Featurization Ordering**: The `ColumnTransformer` is fitted **strictly on the training split** to prevent test data leakage.
   - Continuous numerical features (`tenure`, `monthly_charges`, `total_charges`) are scaled using `StandardScaler`.
   - Categorical features are encoded using `OneHotEncoder(drop='first', sparse_output=False, handle_unknown='ignore')`.

---

## 5. Supervised Classification Models

Two interpretable model architectures are implemented:

1. **Logistic Regression**: Linear probability model (`class_weight='balanced'`, `max_iter=1000`, `random_state=42`).
2. **Decision Tree Classifier**: Pruned non-linear decision tree (`max_depth=5`, `min_samples_leaf=30`, `class_weight='balanced'`, `random_state=42`) balancing expressive logic with strict resistance to overfitting.

---

## 6. Model Evaluation Metrics & Trade-Offs

Both models were evaluated on the independent test set ($N = 1,409$; 1,035 non-churned, 374 churned):

| Metric | Logistic Regression (Balanced) | Decision Tree (Balanced, depth=5) | Operational Trade-off Analysis |
| :--- | :---: | :---: | :--- |
| **Accuracy** | 73.24% | 73.17% | Lower than unweighted (~80%) due to proactive prioritization of minor class. |
| **Precision** | 49.75% | 49.67% | ~50% of flagged accounts churn; half receive retention offers while staying. |
| **Recall (Churn)** | **79.14%** (296 / 374) | **80.48%** (301 / 374) | **Primary Objective**: Captures ~80% of churners; only 73-78 false negatives. |
| **F1-Score** | 0.6109 | 0.6143 | Harmonic mean reflecting strong minority class coverage. |
| **ROC-AUC** | **0.8422** | **0.8294** | Logistic Regression exhibits smoother ranking discrimination across probabilities. |

### Confusion Matrices
- **Logistic Regression**:
  - True Negative (TN): 736 | False Positive (FP): 299
  - False Negative (FN): 78  | True Positive (TP): 296
- **Decision Tree**:
  - True Negative (TN): 730 | False Positive (FP): 305
  - False Negative (FN): 73  | True Positive (TP): 301

---

## 7. Feature Interpretation

Ranked explanatory table comparing Decision Tree Gini importance and Logistic Regression coefficients:

| Feature | DT Importance | LR Coefficient | Statistical Association Direction |
| :--- | :---: | :---: | :--- |
| `Contract_Two year` | **0.4090** | **-1.5259** | Strongly associated with lower predicted churn probability (retention) |
| `Contract_One year` | **0.2558** | **-0.7318** | Associated with lower predicted churn probability (retention) |
| `InternetService_Fiber optic` | **0.1126** | **+1.1949** | Associated with higher predicted churn probability |
| `tenure` | **0.0956** | **-1.0257** | Associated with lower predicted churn probability (retention) |
| `StreamingMovies_Yes` | 0.0357 | +0.4204 | Associated with higher predicted churn probability |
| `PaymentMethod_Electronic check` | 0.0163 | +0.3340 | Associated with higher predicted churn probability |

---

## 8. Network Clustering Objective

The objective of unsupervised clustering is to discover natural, recurring operating regimes in radio access telemetry without human bias or predetermined labels.

---

## 9. KPI Features Used vs. Excluded

### Included (7 Continuous Radio Measurements)
- `latency_ms`
- `throughput_mbps`
- `packet_loss_pct`
- `call_drop_rate_pct`
- `signal_strength_dbm`
- `handover_success_pct`
- `active_connections`

### Excluded (Identifiers & Context)
- `cell_id`, `region`, `technology`, `timestamp`, `network_kpi_key`.

---

## 10. K Selection Process

Evaluated $K \in [2, 3, 4, 5]$ over standardized features ($N = 3,600$):

| Candidate K | Inertia (WCSS) | Silhouette Score | Analytical Assessment |
| :---: | :---: | :---: | :--- |
| **K = 2** | 18,666.45 | **0.8045** | Mathematically separates normal bulk from extreme outliers. |
| **K = 3** | **15,341.73** | **0.7316** | **Selected Demonstration K**: Disaggregates coverage-edge from critical degradation. |
| **K = 4** | 12,222.78 | 0.3002 | Splits normal cluster into LTE vs 5G throughput bands; drops silhouette. |
| **K = 5** | 10,444.40 | 0.3210 | Fragmentation of baseline cluster without additional operational clarity. |

---

## 11. Cluster Interpretation ($K = 3$)

Profiles calculated across original unscaled telemetry measurements:

### Cluster 1: Healthy Baseline Operation (Normal QoS)
- **Observations**: 3,517 (97.69% of network telemetry)
- **Avg Latency**: 17.88 ms
- **Avg Throughput**: 286.47 Mbps
- **Avg Call Drop Rate**: 0.61%
- **Avg Packet Loss**: 0.90%
- **Avg Signal Strength**: -57.41 dBm
- **Interpretation**: Standard operational health with low latency, robust signal, and nominal call drop rates.

### Cluster 0: Weak Signal / Cell Edge (Coverage Gap)
- **Observations**: 43 (1.19% of network telemetry)
- **Avg Latency**: 12.54 ms
- **Avg Throughput**: 368.14 Mbps
- **Avg Call Drop Rate**: 0.52%
- **Avg Packet Loss**: 0.70%
- **Avg Signal Strength**: **-100.20 dBm**
- **Interpretation**: Good throughput and packet delivery despite severely attenuated signal strength, characteristic of user equipment operating at the fringe of a cell tower's coverage boundary.

### Cluster 2: Severe Network Degradation (Critical Outage / Congestion)
- **Observations**: 40 (1.11% of network telemetry)
- **Avg Latency**: **285.03 ms**
- **Avg Throughput**: 270.50 Mbps
- **Avg Call Drop Rate**: **11.87%**
- **Avg Packet Loss**: **19.05%**
- **Avg Signal Strength**: **-103.48 dBm**
- **Interpretation**: Extreme network impairment characterized by massive latency spikes (285 ms), 19% packet loss, and severe call termination (>11%). Corresponds to the severe outage events identified in Step 4 OLAP threshold queries.

---

## 12. Association-Rule Mining

Customer service pattern analysis employs the **Apriori** algorithm to identify bundles and service combinations associated with churn events.

---

## 13. Support

$$\text{Support}(X) = \frac{\text{Count}(X)}{N}$$

Measures how frequently an itemset appears across all 7,043 customer accounts. A minimum support threshold of `min_support = 0.05` ensures rules represent at least 352 customers.

---

## 14. Confidence

$$\text{Confidence}(X \rightarrow Y) = \frac{\text{Support}(X \cup Y)}{\text{Support}(X)}$$

Measures the probability that a customer has cancelled service ($Y = \text{Churn=Yes}$) given that they subscribe to service configuration $X$. Configured to `min_confidence = 0.35` (substantially above the 26.54% base churn rate).

---

## 15. Lift

$$\text{Lift}(X \rightarrow Y) = \frac{\text{Confidence}(X \rightarrow Y)}{\text{Support}(Y)}$$

Measures how much more likely the churn event is when condition $X$ is present compared to random chance. A lift of $1.0$ implies independence; lift $> 2.0$ indicates strong positive statistical association.

### Top Association Rules Targeting `Churn = Yes` (Ranked by Lift)
| Antecedent (Service Configuration) | Consequent | Support | Confidence | Lift |
| :--- | :---: | :---: | :---: | :---: |
| `Contract=Month-to-month & InternetService=Fiber optic` | **Churn=Yes** | 0.1650 | **54.61%** | **2.0577** |
| `OnlineBackup=No & PaymentMethod=Electronic check` | **Churn=Yes** | 0.1093 | **53.92%** | **2.0319** |
| `Contract=Month-to-month & PaymentMethod=Electronic check` | **Churn=Yes** | 0.1411 | **53.73%** | **2.0247** |
| `InternetService=Fiber optic & PaymentMethod=Electronic check` | **Churn=Yes** | 0.1205 | **53.23%** | **2.0058** |
| `PaymentMethod=Electronic check & TechSupport=No` | **Churn=Yes** | 0.1306 | **53.18%** | **2.0040** |

---

## 16. Analytical Limitations

1. **Decoupled Architecture**: Telemetry observations in `FACT_NETWORK_KPI` cannot be linked to specific customer churn rows in `FACT_CUSTOMER_CHURN`.
2. **Cross-Sectional Customer Snapshot**: The churn dataset lacks event timestamps; tenure acts as the sole proxy for subscriber lifecycle duration.
3. **Short Telemetry Window**: Network measurements represent a 30-minute interval on 2026-08-03; clusters reflect micro-level state changes rather than seasonal or diurnal cycles.

---

## 17. How to Execute the Mining Pipeline

Run the automated test and validation suite from the project root:

```powershell
python scripts/test_mining.py
```

### Generated Files
- **Models (`backend/mining/models/`)**:
  - `churn_logistic_regression.joblib`
  - `churn_decision_tree.joblib`
  - `churn_preprocessor.joblib`
  - `network_kmeans.joblib`
  - `clustering_scaler.joblib`
- **Results (`backend/mining/results/`)**:
  - `churn_metrics.json`
  - `churn_feature_importance.csv`
  - `clustering_metrics.json`
  - `cluster_profiles.csv`
  - `association_rules.csv`
