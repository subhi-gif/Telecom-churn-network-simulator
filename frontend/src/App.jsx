import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import OverviewPanel from './components/OverviewPanel';
import NetworkOverview from './components/NetworkOverview';
import OLAPPanel from './components/OLAPPanel';
import MiningPanel from './components/MiningPanel';
import SimulationPanel from './components/SimulationPanel';
import { api } from './services/api';
import { AlertCircle, Terminal, Database, ShieldCheck } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [apiHealthy, setApiHealthy] = useState(null);
  const [checkingHealth, setCheckingHealth] = useState(true);

  // Poll backend health
  const checkHealth = async () => {
    try {
      const res = await api.getHealth();
      const isOnline = res?.status === 'ok' || Boolean(res?.success && res?.data?.status === 'ok');
      setApiHealthy(isOnline);
    } catch {
      setApiHealthy(false);
    } finally {
      setCheckingHealth(false);
    }
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 8000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="dashboard-container">
      {/* Global Application Header & Tab Switcher */}
      <Header 
        activeTab={activeTab} 
        setActiveTab={setActiveTab} 
        apiHealthy={apiHealthy} 
        isBackendOnline={apiHealthy}
      />

      {/* Backend Offline Warning Banner */}
      {apiHealthy === false && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.12)',
          border: '1px solid rgba(239, 68, 68, 0.35)',
          padding: '1rem 1.5rem',
          margin: '1.25rem 2rem 0',
          borderRadius: '10px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '1rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <AlertCircle size={22} color="var(--accent-red)" />
            <div>
              <div style={{ fontWeight: 600, color: '#fca5a5', fontSize: '0.95rem' }}>
                Backend REST API Unreachable (http://127.0.0.1:8000)
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                Please ensure the FastAPI service is running to fetch live warehouse data and simulation states.
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'rgba(0,0,0,0.4)', padding: '0.4rem 0.8rem', borderRadius: '6px' }}>
            <Terminal size={14} color="var(--accent-cyan)" />
            <code style={{ fontSize: '0.8rem', color: 'var(--accent-cyan)' }}>
              python -m uvicorn backend.api.main:app --port 8000
            </code>
          </div>
        </div>
      )}

      {/* Main Tab Content */}
      <main style={{ minHeight: 'calc(100vh - 180px)' }}>
        {activeTab === 'overview' && <OverviewPanel onNavigate={setActiveTab} />}
        {activeTab === 'network' && <NetworkOverview />}
        {activeTab === 'olap' && <OLAPPanel />}
        {activeTab === 'mining' && <MiningPanel />}
        {activeTab === 'simulation' && <SimulationPanel />}
      </main>

      {/* Presentation Footer */}
      <footer style={{
        marginTop: '3rem',
        padding: '1.5rem 2rem',
        borderTop: '1px solid var(--border-subtle)',
        background: 'rgba(15, 23, 42, 0.6)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '1rem',
        fontSize: '0.85rem',
        color: 'var(--text-muted)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <Database size={16} color="var(--accent-cyan)" />
          <span>
            B.Tech Data Warehousing & Data Mining Project | Star Schema Dimensional Warehouse (<code>warehouse.db</code>)
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <ShieldCheck size={16} color="var(--accent-emerald)" />
            Warehouse Immutability Enforced
          </span>
          <span>FastAPI + React 18 + Pure SVG Charts</span>
        </div>
      </footer>
    </div>
  );
}
