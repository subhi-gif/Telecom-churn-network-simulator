import React, { useState, useEffect, useRef } from 'react';
import { api } from '../services/api';
import {
  Activity,
  Play,
  Pause,
  RotateCcw,
  Zap,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  TrendingDown,
  ArrowRight,
  ShieldAlert,
  Flame,
  Clock,
  Trash2,
  Radio,
  Sliders,
  ListOrdered
} from 'lucide-react';

const SCENARIOS = [
  { id: 'NORMAL', label: 'Normal Traffic', desc: 'Standard operating baseline conditions' },
  { id: 'CONGESTION', label: 'Radio Congestion', desc: 'Surge in users causing queuing latency & loss' },
  { id: 'SIGNAL_DEGRADATION', label: 'Signal Degradation', desc: 'Interference / fading lowering RF strength' },
  { id: 'CELL_OVERLOAD', label: 'Cell Overload', desc: 'Excessive connections exhausting bandwidth' },
  { id: 'RECOVERY', label: 'Network Recovery', desc: 'Gradual restoration toward baseline performance' },
];

const SEVERITIES = ['LOW', 'MEDIUM', 'HIGH'];

export default function SimulationPanel() {
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);

  // State from backend
  const [simState, setSimState] = useState(null);
  const [comparison, setComparison] = useState([]);
  const [events, setEvents] = useState([]);

  // Cell list for selection
  const [cells, setCells] = useState([]);
  const [selectedCell, setSelectedCell] = useState('Cell_0025');

  // Scenario selections
  const [scenario, setScenario] = useState('CONGESTION');
  const [severity, setSeverity] = useState('HIGH');

  // Demo workflow state
  const [demoRunning, setDemoRunning] = useState(false);
  const [demoStep, setDemoStep] = useState(0);

  const autoRunTimerRef = useRef(null);

  // 1. Initial load
  useEffect(() => {
    fetchCells();
    fetchState();
    fetchComparison();
    fetchEvents();
  }, []);

  // Fetch cell inventory
  const fetchCells = async () => {
    const res = await api.getCells();
    if (res.success && res.data) {
      setCells(res.data);
    }
  };

  // Fetch simulation state
  const fetchState = async () => {
    const res = await api.getSimulationState();
    if (res.success && res.data) {
      setSimState(res.data);
      if (res.data.cell?.cell_id) {
        setSelectedCell(res.data.cell.cell_id);
      }
      if (res.data.scenario) {
        setScenario(res.data.scenario);
      }
      if (res.data.severity) {
        setSeverity(res.data.severity);
      }
      setRunning(res.data.simulation_active);
    }
  };

  // Fetch comparison deltas
  const fetchComparison = async () => {
    const res = await api.getSimulationComparison();
    if (res.success && Array.isArray(res.data)) {
      const normalized = res.data.map((c) => ({
        ...c,
        kpi: c.metric_key || c.kpi || '',
        name: c.metric_name || (c.metric_key || c.kpi || '').replace(/_/g, ' '),
        baseline: Number(c.baseline ?? 0),
        current: Number(c.simulated ?? c.current ?? 0),
        simulated: Number(c.simulated ?? c.current ?? 0),
        delta: Number(c.absolute_difference ?? c.delta ?? 0),
        absolute_difference: Number(c.absolute_difference ?? c.delta ?? 0),
        pct_delta: c.percentage_difference !== undefined ? c.percentage_difference : (c.pct_delta ?? null),
        percentage_difference: c.percentage_difference !== undefined ? c.percentage_difference : (c.pct_delta ?? null),
      }));
      setComparison(normalized);
    }
  };

  // Fetch event log
  const fetchEvents = async () => {
    const res = await api.getSimulationEvents();
    if (res.success && res.data) {
      setEvents(res.data);
    }
  };

  // Auto-run ticker when running is true
  useEffect(() => {
    if (running) {
      autoRunTimerRef.current = setInterval(async () => {
        const res = await api.updateSimulation(1.0);
        if (res.success && res.data) {
          setSimState(res.data);
          fetchComparison();
          fetchEvents();
        }
      }, 1000);
    } else {
      if (autoRunTimerRef.current) clearInterval(autoRunTimerRef.current);
    }
    return () => {
      if (autoRunTimerRef.current) clearInterval(autoRunTimerRef.current);
    };
  }, [running]);

  // Handle cell selection
  const handleSelectCell = async (cellId) => {
    setLoading(true);
    setError(null);
    setSelectedCell(cellId);
    const res = await api.selectSimulationCell(cellId);
    if (res.success && res.data) {
      setSimState(res.data);
      await fetchComparison();
      await fetchEvents();
    } else {
      setError(res.error?.message || 'Failed to select cell baseline.');
    }
    setLoading(false);
  };

  // Handle Scenario & Severity Apply
  const handleApplyScenario = async (newScen = scenario, newSev = severity) => {
    setLoading(true);
    setError(null);
    const res = await api.applySimulationScenario(newScen, newSev);
    if (res.success && res.data) {
      setSimState(res.data);
      await fetchComparison();
      await fetchEvents();
    } else {
      setError(res.error?.message || 'Failed to apply scenario.');
    }
    setLoading(false);
  };

  // Step Update (+1.0s)
  const handleStepUpdate = async () => {
    setLoading(true);
    setError(null);
    const res = await api.updateSimulation(1.0);
    if (res.success && res.data) {
      setSimState(res.data);
      await fetchComparison();
      await fetchEvents();
    } else {
      setError(res.error?.message || 'Failed to update simulation step.');
    }
    setLoading(false);
  };

  // Toggle Pause/Resume
  const handleToggleRun = async () => {
    setError(null);
    if (running) {
      const res = await api.pauseSimulation();
      if (res.success) {
        setRunning(false);
      }
    } else {
      const res = await api.resumeSimulation();
      if (res.success) {
        setRunning(true);
      }
    }
  };

  // Reset Simulation to pristine baseline
  const handleReset = async () => {
    setLoading(true);
    setRunning(false);
    setError(null);
    const res = await api.resetSimulation();
    if (res.success && res.data) {
      setSimState(res.data);
      setScenario('NORMAL');
      setSeverity('MEDIUM');
      await fetchComparison();
      await fetchEvents();
    } else {
      setError(res.error?.message || 'Failed to reset simulation.');
    }
    setLoading(false);
  };

  // Clear Event Log
  const handleClearEvents = async () => {
    const res = await api.clearSimulationEvents();
    if (res.success) {
      setEvents([]);
    }
  };

  // 1-Click Guided Demonstration Workflow
  const runGuidedDemo = async () => {
    if (demoRunning) return;
    setDemoRunning(true);
    setRunning(false);
    setError(null);

    try {
      // Step 1: Select Cell_0025
      setDemoStep(1);
      await handleSelectCell('Cell_0025');
      await new Promise(r => setTimeout(r, 900));

      // Step 2: Apply CONGESTION HIGH
      setDemoStep(2);
      setScenario('CONGESTION');
      setSeverity('HIGH');
      await handleApplyScenario('CONGESTION', 'HIGH');
      await new Promise(r => setTimeout(r, 900));

      // Step 3: Advance 3 simulation steps to develop degradation
      setDemoStep(3);
      for (let i = 0; i < 3; i++) {
        await api.updateSimulation(1.0);
        await new Promise(r => setTimeout(r, 600));
      }
      await fetchState();
      await fetchComparison();
      await fetchEvents();
      await new Promise(r => setTimeout(r, 1200));

      // Step 4: Apply RECOVERY scenario
      setDemoStep(4);
      setScenario('RECOVERY');
      setSeverity('MEDIUM');
      await handleApplyScenario('RECOVERY', 'MEDIUM');
      await new Promise(r => setTimeout(r, 800));

      // Step 5: Advance 2 recovery steps
      setDemoStep(5);
      for (let i = 0; i < 2; i++) {
        await api.updateSimulation(1.0);
        await new Promise(r => setTimeout(r, 500));
      }
      await fetchState();
      await fetchComparison();
      await fetchEvents();
      setDemoStep(6);
    } catch (err) {
      setError('Guided demo encountered an error.');
    } finally {
      setDemoRunning(false);
    }
  };

  // Health Score Color & Label helper
  const getHealthBadge = (score) => {
    if (score >= 80) return { color: 'var(--accent-emerald)', label: 'OPTIMAL HEALTH', bg: 'rgba(16, 185, 129, 0.15)' };
    if (score >= 60) return { color: 'var(--accent-amber)', label: 'DEGRADED PERFORMANCE', bg: 'rgba(245, 158, 11, 0.15)' };
    return { color: 'var(--accent-red)', label: 'CRITICAL CONGESTION', bg: 'rgba(239, 68, 68, 0.15)' };
  };

  const health = getHealthBadge(simState?.health_score ?? 100);

  return (
    <div className="panel-container">
      {/* Top Banner & Visual Segregation */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Activity size={26} color="var(--accent-amber)" />
            Telecom Network Simulation Engine
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '0.25rem' }}>
            In-memory what-if scenario testing. Evaluates radio access degradation without modifying warehouse records.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <span className="badge badge-simulated">
            [SIMULATED / WHAT-IF DATA]
          </span>
          <button 
            className="btn btn-primary" 
            onClick={runGuidedDemo}
            disabled={demoRunning || loading}
            style={{ background: 'linear-gradient(135deg, #f59e0b, #d97706)', border: 'none' }}
          >
            <Zap size={16} />
            {demoRunning ? `Running Demo (Step ${demoStep}/6)...` : '1-Click Guided Demo'}
          </button>
        </div>
      </div>

      {/* Error alert */}
      {error && (
        <div className="glass-card" style={{ borderColor: 'var(--accent-red)', padding: '1rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <AlertTriangle color="var(--accent-red)" size={20} />
          <span style={{ color: 'var(--accent-red)', fontSize: '0.9rem' }}>{error}</span>
        </div>
      )}

      {/* Guided Demo Progress Bar (when active) */}
      {demoRunning && (
        <div className="glass-card" style={{ padding: '1rem 1.25rem', marginBottom: '1.5rem', borderColor: 'var(--accent-amber)', background: 'rgba(245, 158, 11, 0.05)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--accent-amber)' }}>
              Guided Demo in Progress: Step {demoStep} of 6
            </span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Automated Presentation Sequence</span>
          </div>
          <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden' }}>
            <div style={{ width: `${(demoStep / 6) * 100}%`, height: '100%', background: 'var(--accent-amber)', transition: 'width 0.4s ease' }} />
          </div>
        </div>
      )}

      {/* Section 1: Cell Selector & Controls Bar */}
      <div className="glass-card" style={{ padding: '1.25rem 1.5rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.5rem', alignItems: 'center', justifyContent: 'space-between' }}>
          {/* Cell selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Radio size={18} color="var(--accent-cyan)" />
            <span style={{ fontSize: '0.9rem', fontWeight: 600 }}>Target Cell:</span>
            <select 
              className="select-input" 
              value={selectedCell} 
              onChange={(e) => handleSelectCell(e.target.value)}
              disabled={loading || demoRunning}
              style={{ fontWeight: 600, minWidth: '150px' }}
            >
              {cells.map(c => (
                <option key={c.cell_id} value={c.cell_id}>
                  {c.cell_id} ({c.region} - {c.technology})
                </option>
              ))}
            </select>
            {simState?.cell && (
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginLeft: '0.5rem' }}>
                {simState.cell.region} | {simState.cell.technology}
              </span>
            )}
          </div>

          {/* Execution Controls */}
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <button 
              className="btn btn-secondary" 
              onClick={handleStepUpdate}
              disabled={loading || demoRunning}
              title="Advance simulation by 1.0 second"
            >
              <Zap size={15} />
              Step (+1.0s)
            </button>

            <button 
              className={`btn ${running ? 'btn-secondary' : 'btn-primary'}`}
              onClick={handleToggleRun}
              disabled={loading || demoRunning}
            >
              {running ? (
                <>
                  <Pause size={15} />
                  Pause Auto-Run
                </>
              ) : (
                <>
                  <Play size={15} />
                  Auto-Run (1s Ticker)
                </>
              )}
            </button>

            <button 
              className="btn btn-secondary" 
              onClick={handleReset}
              disabled={loading || demoRunning}
              title="Restore cell to pristine warehouse baseline"
            >
              <RotateCcw size={15} />
              Reset Baseline
            </button>
          </div>
        </div>
      </div>

      {/* Section 2: Scenario Configuration & Health Score Gauge */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem', marginBottom: '1.5rem' }}>
        {/* Scenario Selection Card */}
        <div className="glass-card" style={{ padding: '1.5rem' }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Sliders size={18} color="var(--accent-cyan)" />
            Configure Scenario & Severity
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.35rem' }}>
                Operational Scenario:
              </label>
              <select 
                className="select-input" 
                value={scenario} 
                onChange={(e) => setScenario(e.target.value)}
                disabled={loading || demoRunning}
                style={{ width: '100%', padding: '0.5rem 0.75rem' }}
              >
                {SCENARIOS.map(s => (
                  <option key={s.id} value={s.id}>
                    {s.label} ({s.id})
                  </option>
                ))}
              </select>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.25rem', display: 'block' }}>
                {SCENARIOS.find(s => s.id === scenario)?.desc}
              </span>
            </div>

            <div>
              <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.35rem' }}>
                Degradation Severity:
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem' }}>
                {SEVERITIES.map(sev => (
                  <button
                    key={sev}
                    type="button"
                    className={`btn ${severity === sev ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setSeverity(sev)}
                    disabled={loading || demoRunning}
                    style={{ fontSize: '0.85rem', padding: '0.4rem', justifyContent: 'center' }}
                  >
                    {sev}
                  </button>
                ))}
              </div>
            </div>

            <button 
              className="btn btn-primary" 
              onClick={() => handleApplyScenario(scenario, severity)}
              disabled={loading || demoRunning}
              style={{ marginTop: '0.5rem', justifyContent: 'center' }}
            >
              Apply Scenario to Simulation
            </button>
          </div>
        </div>

        {/* Health Score & Status Gauge Card */}
        <div className="glass-card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Activity size={18} color={health.color} />
                Radio Cell Health Score
              </h3>
              <span className="badge" style={{ background: health.bg, color: health.color, border: `1px solid ${health.color}40` }}>
                {health.label}
              </span>
            </div>

            {/* Gauge visualization */}
            <div style={{ textAlign: 'center', padding: '1.5rem 0' }}>
              <div style={{ fontSize: '3.5rem', fontWeight: 800, color: health.color, fontFamily: 'var(--font-mono)', lineHeight: 1 }}>
                {simState?.health_score !== undefined ? simState.health_score : '--'}
                <span style={{ fontSize: '1.5rem', fontWeight: 500, color: 'var(--text-muted)', marginLeft: '0.25rem' }}>/100</span>
              </div>
              <div style={{ marginTop: '0.75rem', width: '100%', height: '8px', background: 'rgba(255,255,255,0.08)', borderRadius: '4px', overflow: 'hidden' }}>
                <div 
                  style={{ 
                    width: `${simState?.health_score || 0}%`, 
                    height: '100%', 
                    background: health.color, 
                    transition: 'width 0.4s ease, background 0.4s ease' 
                  }} 
                />
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', color: 'var(--text-muted)', borderTop: '1px solid var(--border-subtle)', paddingTop: '0.75rem' }}>
            <span>Active Scenario: <strong>{simState?.scenario || 'NORMAL'}</strong></span>
            <span>Elapsed Sim Time: <strong>{simState?.simulation_time || 0}s</strong></span>
          </div>
        </div>
      </div>

      {/* Section 3: Generated Degradation Alerts */}
      <div className="glass-card" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h3 style={{ fontSize: '1.15rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <ShieldAlert size={18} color="var(--accent-red)" />
            Real-Time Degradation Alerts
          </h3>
          <span className="badge badge-simulated">[SIMULATED CONDITION]</span>
        </div>

        {simState?.alerts && simState.alerts.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {simState.alerts.map((alt, idx) => (
              <div 
                key={idx} 
                style={{ 
                  padding: '0.85rem 1.25rem', 
                  background: 'rgba(239, 68, 68, 0.1)', 
                  border: '1px solid rgba(239, 68, 68, 0.3)', 
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem'
                }}
              >
                <Flame size={18} color="var(--accent-red)" />
                <span style={{ fontSize: '0.9rem', color: '#fca5a5', fontWeight: 500 }}>
                  {typeof alt === 'string' ? alt : (alt?.message || alt?.alert_type || 'Degradation condition detected')}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-muted)', background: 'rgba(255,255,255,0.02)', borderRadius: '8px' }}>
            <CheckCircle2 size={24} color="var(--accent-emerald)" style={{ margin: '0 auto 0.5rem', display: 'block' }} />
            No degradation alerts active. Cell operating within standard radio thresholds.
          </div>
        )}
      </div>

      {/* Section 4: Baseline vs. Simulated Comparison Table */}
      <div className="glass-card" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <h3 style={{ fontSize: '1.15rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <ListOrdered size={18} color="var(--accent-cyan)" />
            Baseline vs. Simulated Performance Comparison
          </h3>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <span className="badge badge-real">[REAL BASELINE]</span>
            <span className="badge badge-simulated">[SIMULATED STATE]</span>
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>KPI Metric</th>
                <th>Baseline (Warehouse)</th>
                <th>Simulated Value</th>
                <th>Absolute Delta</th>
                <th>% Delta</th>
                <th>Impact Direction</th>
              </tr>
            </thead>
            <tbody>
              {comparison.map((c, i) => {
                const kpi = String(c?.metric_key || c?.kpi || '').toLowerCase();
                const displayName = c?.metric_name || (c?.kpi || c?.metric_key || '').replace(/_/g, ' ') || 'Metric';
                const baselineVal = Number(c?.baseline ?? 0);
                const currentVal = Number(c?.simulated ?? c?.current ?? 0);
                const deltaVal = Number(c?.absolute_difference ?? c?.delta ?? 0);
                const pctDeltaVal = c?.percentage_difference ?? c?.pct_delta ?? null;

                const isWorse = 
                  (kpi.includes('latency') && deltaVal > 0) ||
                  (kpi.includes('drop') && deltaVal > 0) ||
                  (kpi.includes('loss') && deltaVal > 0) ||
                  (kpi.includes('throughput') && deltaVal < 0) ||
                  (kpi.includes('signal') && deltaVal < 0) ||
                  (kpi.includes('handover') && deltaVal < 0);

                const isNeutral = deltaVal === 0;

                return (
                  <tr key={i}>
                    <td style={{ fontWeight: 600, textTransform: 'capitalize' }}>
                      {displayName}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>
                      {baselineVal.toFixed(2)}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: isWorse ? 'var(--accent-red)' : 'var(--text-primary)' }}>
                      {currentVal.toFixed(2)}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>
                      {deltaVal > 0 ? `+${deltaVal.toFixed(2)}` : deltaVal.toFixed(2)}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                      {pctDeltaVal !== null && !isNaN(Number(pctDeltaVal)) ? `${Number(pctDeltaVal) > 0 ? '+' : ''}${Number(pctDeltaVal).toFixed(1)}%` : 'N/A'}
                    </td>
                    <td>
                      {isNeutral ? (
                        <span className="badge badge-neutral">Nominal</span>
                      ) : isWorse ? (
                        <span className="badge badge-danger" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                          <TrendingDown size={13} />
                          Degraded
                        </span>
                      ) : (
                        <span className="badge badge-success" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                          <TrendingUp size={13} />
                          Nominal
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Section 5: Chronological Simulation Event Log */}
      <div className="glass-card" style={{ padding: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <h3 style={{ fontSize: '1.15rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Clock size={18} color="var(--accent-purple)" />
            In-Memory Simulation Audit Log ({events.length} events)
          </h3>
          <button 
            className="btn btn-secondary" 
            onClick={handleClearEvents} 
            disabled={events.length === 0}
            style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}
          >
            <Trash2 size={14} />
            Clear Log
          </button>
        </div>

        <div style={{ maxHeight: '280px', overflowY: 'auto' }}>
          {events.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {events.slice().reverse().map((ev, idx) => (
                <div 
                  key={idx}
                  style={{ 
                    padding: '0.65rem 1rem', 
                    background: 'rgba(255, 255, 255, 0.02)', 
                    border: '1px solid var(--border-subtle)', 
                    borderRadius: '6px',
                    fontSize: '0.85rem',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '0.5rem'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                    <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>
                      T+{ev.simulation_time ?? 0}s
                    </span>
                    <span style={{ fontWeight: 600 }}>{ev.scenario || 'EVENT'}</span>
                    {ev.severity && <span className="badge badge-neutral">{ev.severity}</span>}
                    <span style={{ color: 'var(--text-muted)' }}>{ev.message || ev.action || 'Simulation updated'}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    {ev.health_score !== undefined && (
                      <span style={{ fontFamily: 'var(--font-mono)', color: ev.health_score >= 80 ? 'var(--accent-emerald)' : 'var(--accent-red)' }}>
                        Health: {ev.health_score}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--text-muted)' }}>
              No simulation events logged in current session.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
