# Telecom Churn & Network Simulator — Interactive Frontend Dashboard

## Executive Overview
The **Interactive Frontend Dashboard** serves as the unified visualization and exploration interface for the Telecom Churn & Network Simulator capstone project. Built with **React 18**, **Vite 5**, and a custom dark-mode glassmorphic design system with zero-dependency **pure SVG charts**, the dashboard connects seamlessly to the FastAPI REST API layer (`http://127.0.0.1:8000`).

---

## Strict Source Segregation Principle
To uphold data integrity and academic rigor for a B.Tech Data Warehousing & Data Mining (DWDM) project:
- **`[REAL WAREHOUSE DATA]`**: Applied across all historical facts, OLAP cubes, customer churn predictions, and network KPI analytics originating from `database/warehouse.db`.
- **`[SIMULATED / WHAT-IF DATA]`**: Applied exclusively to the in-memory simulation engine where operators test degradation scenarios (e.g., Congestion, Signal Degradation, Cell Overload) without altering persistent warehouse records.

---

## Tech Stack & Architecture
- **Framework**: React 18 with Fast Refresh
- **Bundler & Dev Server**: Vite 5
- **Styling**: Vanilla CSS tokens, glassmorphism, responsive CSS grid/flexbox
- **Icons**: Lucide React
- **Visualizations**: Custom Pure SVG responsive vector charts (line graphs with gradient fills, grid lines, and interactive hover tooltips)
- **API Client**: Centralized asynchronous service (`frontend/src/services/api.js`) consuming 24 REST endpoints

---

## Directory Structure
```
frontend/
├── index.html               # Main HTML entry with Inter & JetBrains Mono typography
├── package.json             # React 18, Vite 5, Lucide React dependencies
├── vite.config.js           # Vite configuration with API proxy to port 8000
├── .env                     # Local environment configuration (VITE_API_BASE_URL)
├── .env.example             # Example environment configuration
├── src/
│   ├── main.jsx             # React DOM root entry point
│   ├── App.jsx              # Main application shell, header, health check & tab routing
│   ├── styles/
│   │   └── index.css        # Design tokens, glassmorphism, badges, and layout utilities
│   ├── services/
│   │   └── api.js           # Centralized API service for all 24 backend endpoints
│   └── components/
│       ├── Header.jsx       # Branding, navigation bar, and API connectivity indicator
│       ├── KPI_Cards.jsx    # Reusable KPI metric card with trend and source badge
│       ├── LineChart.jsx    # Pure SVG time-series visualization with tooltips
│       ├── OverviewPanel.jsx# Platform KPI summary & Star Schema dimensional architecture
│       ├── NetworkOverview.jsx # Cell inventory browser & 4 KPI time series charts
│       ├── OLAPPanel.jsx    # Multidimensional slices, dice, rollup, and drilldown
│       ├── MiningPanel.jsx  # Supervised churn models, K-Means clustering, Apriori rules
│       └── SimulationPanel.jsx # What-if simulator, health gauge, deltas, and demo workflow
└── README.md                # Documentation and operational manual
```

---

## Getting Started

### Prerequisites
- **Node.js**: v18.0.0+ or v20.x LTS
- **FastAPI Backend Server**: Running on `http://127.0.0.1:8000`

### 1. Start the Backend API Server
In a dedicated terminal from the project root:
```bash
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000
```
Verify the backend is live at [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health).

### 2. Install Frontend Dependencies
```bash
cd frontend
npm install
```

### 3. Run Development Server
```bash
npm run dev
```
The application will launch at [http://localhost:5173](http://localhost:5173).

### 4. Build for Production
```bash
npm run build
npm run preview
```

---

## Dashboard Sections

### 1. Overview & Data Architecture
- **Summary Metrics**: Real warehouse facts highlighting 7,043 customers (26.54% churn rate) and 3,600 radio network KPI readings across 25 cell towers.
- **Dimensional Schema Tables**: Detailed breakdown of Customer Churn and Network Performance star schemas including primary keys, surrogate keys, dimension attributes, and additive fact measures.

### 2. Radio Network Analysis
- **Cell Inventory Selector**: Dynamic filtering by Region (North, South, East, West, Central) and Technology (3G, 4G, 5G). Defaults to reference cell **`Cell_0025`** (`Central`, `5G`).
- **Telemetry Charts**: 4 pure SVG time-series charts displaying Latency (ms), Throughput (Mbps), Call Drop Rate (%), and Packet Loss (%).

### 3. Multidimensional OLAP Engine
- **Customer Churn Mart**: Roll-up by contract, Drill-down by tenure band, Slice by internet service / tech support, and Dice across contract and payment method.
- **Network Performance Mart**: Roll-up by hour/day/week/month, Drill-down by region to cell tower, Slice by radio technology, Dice filtering, and High Call Drop anomaly detection (>2.0%).

### 4. Data Mining & ML Models
- **Supervised Churn Prediction**: Logistic Regression vs. Decision Tree evaluation (Accuracy, Precision, Recall, F1, ROC-AUC), confusion matrices, and ranked explanatory feature importances.
- **Unsupervised K-Means Clustering**: Evaluation across K=2..5 with Inertia and Silhouette scores. Cluster profiles for demonstration K=3 (Low, Moderate, High Degradation).
- **Association Rule Mining (Apriori)**: Service patterns mined with Antecedent $\to$ Consequent, Support, Confidence, and Lift. High churn affinity rules tagged.

### 5. Telecom Network Simulation Engine
- **Target Cell Selection**: Loads real baseline conditions from `warehouse.db`.
- **Scenario & Severity**: Apply `NORMAL`, `CONGESTION`, `SIGNAL_DEGRADATION`, `CELL_OVERLOAD`, or `RECOVERY` at `LOW`, `MEDIUM`, or `HIGH` severity.
- **Radio Health Score**: Live computed gauge (0–100) reflecting instantaneous radio network health.
- **Alerts Panel**: Displays active degradation thresholds with explicit `[SIMULATED CONDITION]` badge.
- **Performance Delta Comparison**: Baseline vs. Simulated table with absolute and percentage deltas.
- **1-Click Guided Demonstration**: Automates the entire capstone presentation workflow:
  1. Selects reference cell `Cell_0025`.
  2. Applies `CONGESTION` scenario at `HIGH` severity.
  3. Evolves simulated degradation over multiple steps.
  4. Triggers radio alerts and demonstrates performance deltas.
  5. Applies `RECOVERY` and restores baseline health.

---

## Warehouse Immutability Guarantee
The simulation engine executes purely in memory. SQLite `PRAGMA integrity_check` and record counts (`FACT_CUSTOMER_CHURN = 7,043`, `FACT_NETWORK_KPI = 3,600`) remain completely invariant regardless of simulation actions.
