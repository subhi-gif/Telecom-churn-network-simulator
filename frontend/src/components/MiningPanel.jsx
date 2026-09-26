import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { 
  BrainCircuit, 
  Target, 
  GitBranch, 
  Layers, 
  Sparkles, 
  CheckCircle2, 
  TrendingUp, 
  AlertTriangle,
  RefreshCw,
  Search,
  Filter
} from 'lucide-react';

/**
 * Robust numerical formatter to guard against calling .toFixed on null/undefined values.
 */
const safeToFixed = (val, digits = 2, fallback = null) => {
  if (val === null || val === undefined || val === '') {
    return fallback !== null ? fallback : (0).toFixed(digits);
  }
  const num = Number(val);
  return isNaN(num) ? (fallback !== null ? fallback : (0).toFixed(digits)) : num.toFixed(digits);
};

export default function MiningPanel() {
  const [subTab, setSubTab] = useState('churn'); // 'churn', 'clustering', 'association'
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Data states
  const [churnData, setChurnData] = useState(null);
  const [clusterData, setClusterData] = useState(null);
  const [ruleData, setRuleData] = useState(null);

  // Association Rule filters
  const [churnOnly, setChurnOnly] = useState(true);
  const [minConfidence, setMinConfidence] = useState(0.5);
  const [ruleSearch, setRuleSearch] = useState('');

  // Fetch Churn data
  const fetchChurn = async () => {
    setLoading(true);
    setError(null);
    const res = await api.getMiningChurn();
    if (res.success) {
      setChurnData(res.data);
    } else {
      setError(res.error?.message || 'Failed to load churn models.');
    }
    setLoading(false);
  };

  // Fetch Clustering data
  const fetchClusters = async () => {
    setLoading(true);
    setError(null);
    const res = await api.getMiningClusters();
    if (res.success) {
      setClusterData(res.data);
    } else {
      setError(res.error?.message || 'Failed to load clustering results.');
    }
    setLoading(false);
  };

  // Fetch Association Rules
  const fetchRules = async () => {
    setLoading(true);
    setError(null);
    const res = await api.getMiningAssociationRules({
      churn_only: churnOnly,
      min_confidence: minConfidence,
      limit: 50,
    });
    if (res.success) {
      setRuleData(res.data);
    } else {
      setError(res.error?.message || 'Failed to load association rules.');
    }
    setLoading(false);
  };

  useEffect(() => {
    if (subTab === 'churn' && !churnData) {
      fetchChurn();
    } else if (subTab === 'clustering' && !clusterData) {
      fetchClusters();
    } else if (subTab === 'association') {
      fetchRules();
    }
  }, [subTab, churnOnly, minConfidence]);

  return (
    <div className="panel-container">
      {/* Title & Segregation Badge */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <BrainCircuit size={26} color="var(--accent-cyan)" />
            Data Mining & Machine Learning Layer
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '0.25rem' }}>
            Pre-computed models, evaluations, and pattern rules executed against authentic data warehouse facts.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <span className="badge badge-real">
            [REAL WAREHOUSE DATA]
          </span>
          <button 
            className="btn btn-secondary" 
            onClick={() => {
              if (subTab === 'churn') fetchChurn();
              else if (subTab === 'clustering') fetchClusters();
              else fetchRules();
            }}
            disabled={loading}
          >
            <RefreshCw size={15} className={loading ? 'spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Sub-tab navigation */}
      <div className="tab-bar" style={{ marginBottom: '1.5rem', borderBottom: '1px solid var(--border-subtle)' }}>
        <button 
          className={`tab-btn ${subTab === 'churn' ? 'active' : ''}`}
          onClick={() => setSubTab('churn')}
        >
          <Target size={16} />
          Customer Churn Prediction
        </button>
        <button 
          className={`tab-btn ${subTab === 'clustering' ? 'active' : ''}`}
          onClick={() => setSubTab('clustering')}
        >
          <Layers size={16} />
          Network Degradation Clustering
        </button>
        <button 
          className={`tab-btn ${subTab === 'association' ? 'active' : ''}`}
          onClick={() => setSubTab('association')}
        >
          <Sparkles size={16} />
          Service Pattern Mining (Apriori)
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="glass-card" style={{ borderColor: 'var(--accent-red)', padding: '1rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <AlertTriangle color="var(--accent-red)" size={20} />
          <span style={{ color: 'var(--accent-red)', fontSize: '0.9rem' }}>{error}</span>
        </div>
      )}

      {/* Loading Indicator */}
      {loading && !churnData && !clusterData && !ruleData && (
        <div style={{ textAlign: 'center', padding: '3rem 0', color: 'var(--text-muted)' }}>
          <RefreshCw size={28} className="spin" style={{ margin: '0 auto 1rem', display: 'block' }} />
          Loading analytical models...
        </div>
      )}

      {/* SUB-TAB 1: CUSTOMER CHURN PREDICTION */}
      {subTab === 'churn' && churnData && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Model Comparison Table */}
          <div className="glass-card" style={{ padding: '1.5rem' }}>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 600, marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Target size={18} color="var(--accent-cyan)" />
              Supervised Classification Models Comparison
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '1rem' }}>
              Target variable: <code>churn_flag (0 = Retained, 1 = Churned)</code>. Train/Test split: 80% / 20% stratified.
            </p>

            <div style={{ overflowX: 'auto' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Model Architecture</th>
                    <th>Accuracy</th>
                    <th>Precision</th>
                    <th>Recall</th>
                    <th>F1 Score</th>
                    <th>ROC-AUC</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(churnData.evaluation_metrics || {}).map(([modelKey, m]) => {
                    const isBest = modelKey === 'logistic_regression';
                    const accuracy = m.accuracy != null ? m.accuracy * 100 : undefined;
                    const precision = m.precision != null ? m.precision * 100 : undefined;
                    const recall = m.recall != null ? m.recall * 100 : undefined;
                    const f1 = m.f1_score ?? m.f1;
                    const rocAuc = m.roc_auc ?? m.rocAuc;
                    return (
                      <tr key={modelKey}>
                        <td style={{ fontWeight: 600, textTransform: 'capitalize' }}>
                          {modelKey.replace('_', ' ')}
                          {isBest && <span style={{ marginLeft: '0.5rem', fontSize: '0.75rem', color: 'var(--accent-cyan)' }}>(Recommended)</span>}
                        </td>
                        <td>{safeToFixed(accuracy, 2)}%</td>
                        <td>{safeToFixed(precision, 2)}%</td>
                        <td>{safeToFixed(recall, 2)}%</td>
                        <td style={{ fontWeight: 600, color: 'var(--accent-amber)' }}>{safeToFixed(f1, 4)}</td>
                        <td style={{ fontWeight: 700, color: 'var(--accent-cyan)' }}>{safeToFixed(rocAuc, 4)}</td>
                        <td>
                          <span className="badge badge-success">VALIDATED</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Trade-off Analysis note */}
            {churnData.trade_off_analysis && (
              <div style={{ marginTop: '1rem', padding: '0.85rem 1rem', background: 'rgba(255, 255, 255, 0.03)', borderRadius: '8px', borderLeft: '3px solid var(--accent-cyan)' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  <strong>Trade-off Analysis: </strong>{churnData.trade_off_analysis}
                </span>
              </div>
            )}
          </div>

          {/* Confusion Matrices */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.25rem' }}>
            {Object.entries(churnData.evaluation_metrics || {}).map(([modelKey, m]) => {
              const cm = m.confusion_matrix || {};
              return (
                <div key={modelKey} className="glass-card" style={{ padding: '1.25rem' }}>
                  <h4 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.75rem', textTransform: 'capitalize' }}>
                    {modelKey.replace('_', ' ')} Confusion Matrix
                  </h4>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', textAlign: 'center' }}>
                    <div style={{ padding: '0.85rem', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.25)', borderRadius: '8px' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>True Negative (TN)</div>
                      <div style={{ fontSize: '1.35rem', fontWeight: 700, color: 'var(--accent-emerald)' }}>{cm.true_negative ?? cm.tn ?? '-'}</div>
                    </div>
                    <div style={{ padding: '0.85rem', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.25)', borderRadius: '8px' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>False Positive (FP)</div>
                      <div style={{ fontSize: '1.35rem', fontWeight: 700, color: 'var(--accent-red)' }}>{cm.false_positive ?? cm.fp ?? '-'}</div>
                    </div>
                    <div style={{ padding: '0.85rem', background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.25)', borderRadius: '8px' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>False Negative (FN)</div>
                      <div style={{ fontSize: '1.35rem', fontWeight: 700, color: 'var(--accent-amber)' }}>{cm.false_negative ?? cm.fn ?? '-'}</div>
                    </div>
                    <div style={{ padding: '0.85rem', background: 'rgba(56, 189, 248, 0.1)', border: '1px solid rgba(56, 189, 248, 0.25)', borderRadius: '8px' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>True Positive (TP)</div>
                      <div style={{ fontSize: '1.35rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>{cm.true_positive ?? cm.tp ?? '-'}</div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Feature Importance Table */}
          <div className="glass-card" style={{ padding: '1.5rem' }}>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 600, marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <TrendingUp size={18} color="var(--accent-emerald)" />
              Ranked Explanatory Feature Importances
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '1rem' }}>
              Key drivers of subscriber churn derived from Logistic Regression standardized weights and Decision Tree Gini importance.
            </p>

            <div style={{ overflowX: 'auto', maxHeight: '400px' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Feature Name</th>
                    <th>Logistic Regression Weight</th>
                    <th>Decision Tree Gini</th>
                    <th>Primary Impact</th>
                  </tr>
                </thead>
                <tbody>
                  {(churnData.feature_importances || []).slice(0, 15).map((f, i) => {
                    const lrWeightRaw = f.logistic_regression_coefficient ?? f.lr_coefficient ?? f.lr_weight ?? 0;
                    const lrWeight = parseFloat(lrWeightRaw);
                    const dtGini = parseFloat(f.decision_tree_importance ?? f.dt_importance ?? 0);
                    const isPositiveChurn = lrWeight > 0;

                    return (
                      <tr key={i}>
                        <td style={{ fontWeight: 600 }}>{f.feature || f.feature_name}</td>
                        <td style={{ fontFamily: 'var(--font-mono)', color: isPositiveChurn ? 'var(--accent-red)' : 'var(--accent-emerald)' }}>
                          {lrWeight > 0 ? `+${safeToFixed(lrWeight, 4)}` : safeToFixed(lrWeight, 4)}
                        </td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>{safeToFixed(dtGini, 4)}</td>
                        <td>
                          <span className={`badge ${isPositiveChurn ? 'badge-danger' : 'badge-success'}`}>
                            {isPositiveChurn ? 'Increases Churn' : 'Promotes Retention'}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB 2: NETWORK DEGRADATION CLUSTERING */}
      {subTab === 'clustering' && clusterData && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Clustering Evaluation (K=2..5) */}
          <div className="glass-card" style={{ padding: '1.5rem' }}>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 600, marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Layers size={18} color="var(--accent-cyan)" />
              Unsupervised K-Means Parameter Evaluation (K=2 to K=5)
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '1rem' }}>
              Inertia (Elbow method) and Silhouette score evaluated over standardized 3,600 network KPI observations.
            </p>

            <div style={{ overflowX: 'auto' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Clusters (K)</th>
                    <th>Inertia</th>
                    <th>Silhouette Score</th>
                    <th>Domain Interpretability</th>
                    <th>Demonstration Status</th>
                  </tr>
                </thead>
                <tbody>
                  {(() => {
                    const kList = Array.isArray(clusterData.k_evaluation)
                      ? clusterData.k_evaluation.map(item => ({
                          kVal: item?.k,
                          inertia: item?.inertia,
                          silhouette: item?.silhouette_score
                        }))
                      : Object.entries(clusterData.k_evaluation || {}).map(([kKey, val]) => ({
                          kVal: val?.k ?? kKey.replace('k_', ''),
                          inertia: val?.inertia,
                          silhouette: val?.silhouette_score
                        }));

                    return kList.map((row, idx) => {
                      const isSelected = String(row.kVal) === String(clusterData.selected_k);
                      return (
                        <tr key={idx} style={isSelected ? { background: 'rgba(56, 189, 248, 0.08)' } : {}}>
                          <td style={{ fontWeight: 700, fontSize: '1rem' }}>K = {row.kVal ?? idx}</td>
                          <td style={{ fontFamily: 'var(--font-mono)' }}>{safeToFixed(row.inertia, 2)}</td>
                          <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--accent-cyan)' }}>
                            {safeToFixed(row.silhouette, 4)}
                          </td>
                          <td>
                            {String(row.kVal) === '3' ? 'Optimal: Low, Moderate, High Degradation' : 'Sub-optimal separation'}
                          </td>
                          <td>
                            {isSelected ? (
                              <span className="badge badge-success">SELECTED DEMO K={clusterData.selected_k}</span>
                            ) : (
                              <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Evaluated</span>
                            )}
                          </td>
                        </tr>
                      );
                    });
                  })()}
                </tbody>
              </table>
            </div>

            {clusterData.selection_rationale && (
              <div style={{ marginTop: '1rem', padding: '0.85rem 1rem', background: 'rgba(255, 255, 255, 0.03)', borderRadius: '8px', borderLeft: '3px solid var(--accent-emerald)' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  <strong>Selection Rationale: </strong>{clusterData.selection_rationale}
                </span>
              </div>
            )}
          </div>

          {/* Cluster Profiles for K=3 */}
          <div>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 600, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Sparkles size={18} color="var(--accent-amber)" />
              Degradation Profiles for K={clusterData.selected_k || 3}
            </h3>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.25rem' }}>
              {(clusterData.cluster_profiles || []).map((cp, idx) => {
                const clusterName = cp.cluster_name || cp.profile_name || `Cluster ${cp.cluster_id ?? idx}`;
                const severity = cp.severity || cp.degradation_level || (idx === 0 ? 'Low' : idx === 1 ? 'Moderate' : 'High');
                const badgeColor = severity.toLowerCase().includes('low') 
                  ? 'badge-success' 
                  : severity.toLowerCase().includes('high') 
                    ? 'badge-danger' 
                    : 'badge-warning';

                return (
                  <div key={idx} className="glass-card" style={{ padding: '1.5rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                      <h4 style={{ fontSize: '1.05rem', fontWeight: 700 }}>
                        {clusterName}
                      </h4>
                      <span className={`badge ${badgeColor}`}>{severity} Degradation</span>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', fontSize: '0.9rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-muted)' }}>Latency (ms):</span>
                        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{safeToFixed(cp.latency_ms ?? cp.mean_latency, 1)}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-muted)' }}>Throughput (Mbps):</span>
                        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{safeToFixed(cp.throughput_mbps ?? cp.mean_throughput, 1)}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-muted)' }}>Call Drop Rate:</span>
                        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--accent-red)' }}>
                          {safeToFixed(cp.call_drop_rate_pct ?? cp.mean_call_drop, 2)}%
                        </span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-muted)' }}>Packet Loss:</span>
                        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                          {safeToFixed(cp.packet_loss_pct ?? cp.mean_packet_loss, 2)}%
                        </span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-muted)' }}>Signal Strength (dBm):</span>
                        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                          {safeToFixed(cp.signal_strength_dbm ?? cp.mean_signal, 1)}
                        </span>
                      </div>
                      {(cp.cell_count || cp.observation_count) && (
                        <div style={{ display: 'flex', justifyContent: 'space-between', paddingTop: '0.5rem', borderTop: '1px solid var(--border-subtle)', marginTop: '0.4rem' }}>
                          <span style={{ color: 'var(--text-muted)' }}>Assigned Observations:</span>
                          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--accent-cyan)' }}>
                            {cp.cell_count || cp.observation_count}
                            {cp.network_share_pct ? ` (${safeToFixed(cp.network_share_pct, 1)}%)` : ''}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB 3: CUSTOMER SERVICE PATTERN MINING (APRIORI) */}
      {subTab === 'association' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Filter Controls */}
          <div className="glass-card" style={{ padding: '1.25rem', display: 'flex', flexWrap: 'wrap', gap: '1.5rem', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.25rem', alignItems: 'center' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.9rem', fontWeight: 600 }}>
                <input 
                  type="checkbox" 
                  checked={churnOnly} 
                  onChange={(e) => setChurnOnly(e.target.checked)}
                  style={{ accentColor: 'var(--accent-cyan)', width: '16px', height: '16px' }}
                />
                Filter Target: Churn = Yes
              </label>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Min Confidence:</span>
                <select 
                  className="select-input" 
                  value={minConfidence} 
                  onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
                  style={{ padding: '0.35rem 0.75rem' }}
                >
                  <option value={0.3}>30%</option>
                  <option value={0.4}>40%</option>
                  <option value={0.5}>50% (Default)</option>
                  <option value={0.6}>60%</option>
                  <option value={0.7}>70%</option>
                </select>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', minWidth: '220px' }}>
              <Search size={16} color="var(--text-muted)" />
              <input 
                type="text" 
                placeholder="Search rule antecedents..." 
                className="select-input"
                style={{ width: '100%', padding: '0.35rem 0.75rem' }}
                value={ruleSearch}
                onChange={(e) => setRuleSearch(e.target.value)}
              />
            </div>
          </div>

          {/* Rules Table */}
          <div className="glass-card" style={{ padding: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Sparkles size={18} color="var(--accent-cyan)" />
                Mined Association Rules (Sorted by Lift Descending)
              </h3>
              {ruleData && (
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                  Showing {ruleData.filtered_rules_count} of {ruleData.total_rules_available} total rules
                </span>
              )}
            </div>

            <div style={{ overflowX: 'auto', maxHeight: '480px' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Rule Antecedents (IF)</th>
                    <th>Consequent (THEN)</th>
                    <th>Support</th>
                    <th>Confidence</th>
                    <th>Lift</th>
                    <th>Pattern Strength</th>
                  </tr>
                </thead>
                <tbody>
                  {ruleData?.rules?.filter(r => {
                    if (!ruleSearch) return true;
                    return String(r.antecedents || r.antecedent || '').toLowerCase().includes(ruleSearch.toLowerCase());
                  }).map((r, idx) => {
                    const lift = r.lift != null ? parseFloat(r.lift) : 0;
                    const conf = r.confidence != null ? parseFloat(r.confidence) : 0;
                    const supp = r.support != null ? parseFloat(r.support) : 0;

                    return (
                      <tr key={idx}>
                        <td style={{ fontWeight: 500, maxWidth: '350px' }}>
                          <code>{r.antecedents || r.antecedent}</code>
                        </td>
                        <td>
                          <span className="badge badge-warning">{r.consequents || r.consequent}</span>
                        </td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>{safeToFixed(supp * 100, 2)}%</td>
                        <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{safeToFixed(conf * 100, 2)}%</td>
                        <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: lift > 1.5 ? 'var(--accent-red)' : 'var(--accent-cyan)' }}>
                          {safeToFixed(lift, 2)}x
                        </td>
                        <td>
                          {lift > 2.0 ? (
                            <span className="badge badge-danger">High Affinity</span>
                          ) : lift > 1.3 ? (
                            <span className="badge badge-warning">Moderate Affinity</span>
                          ) : (
                            <span className="badge badge-neutral">Baseline</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                  {(!ruleData?.rules || ruleData.rules.length === 0) && (
                    <tr>
                      <td colSpan={6} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                        No association rules match current filter thresholds.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
