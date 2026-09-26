import React from 'react';
import { Activity, BarChart2, Cpu, Database, Network, ShieldCheck, Wifi } from 'lucide-react';

export default function Header({ activeTab, setActiveTab, isBackendOnline }) {
  const tabs = [
    { id: 'overview', label: 'Overview', icon: <Activity size={16} /> },
    { id: 'network', label: 'Network Analysis', icon: <Wifi size={16} /> },
    { id: 'olap', label: 'OLAP Analysis', icon: <Database size={16} /> },
    { id: 'mining', label: 'Churn & Mining', icon: <BarChart2 size={16} /> },
    { id: 'simulation', label: 'Simulation', icon: <Cpu size={16} /> },
  ];

  return (
    <header className="header-bar">
      <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div
            style={{
              width: '38px',
              height: '38px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #0284c7 0%, #3b82f6 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 16px rgba(2, 132, 199, 0.4)',
            }}
          >
            <Network size={22} color="#fff" />
          </div>
          <div>
            <h1 className="brand-title">Telecom Churn & Network Analysis</h1>
            <p className="brand-subtitle">Data Warehousing, Data Mining & Network Simulation</p>
          </div>
        </div>

        {/* Backend Connectivity Status Pill */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            padding: '0.2rem 0.6rem',
            borderRadius: '9999px',
            background: isBackendOnline ? 'rgba(16, 185, 129, 0.12)' : 'rgba(239, 68, 68, 0.12)',
            border: `1px solid ${isBackendOnline ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
            fontSize: '0.75rem',
            fontWeight: 600,
            color: isBackendOnline ? '#34d399' : '#f87171',
          }}
          title={isBackendOnline ? 'FastAPI Backend connected on port 8000' : 'Backend API is unreachable'}
        >
          <div
            style={{
              width: '7px',
              height: '7px',
              borderRadius: '50%',
              backgroundColor: isBackendOnline ? '#10b981' : '#ef4444',
            }}
          />
          {isBackendOnline ? 'API ONLINE' : 'API OFFLINE'}
        </div>
      </div>

      {/* Primary Navigation Tabs */}
      <nav className="tab-nav">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </nav>
    </header>
  );
}
