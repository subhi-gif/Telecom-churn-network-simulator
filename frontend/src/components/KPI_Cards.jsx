import React from 'react';
import { Database, Cpu, TrendingUp, TrendingDown, Minus } from 'lucide-react';

export function MetricCard({
  title,
  value,
  unit = '',
  subtitle,
  source = 'warehouse', // 'warehouse' or 'simulation'
  trend, // 'up', 'down', 'neutral'
  trendLabel,
  color,
}) {
  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
          <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: 500 }}>{title}</span>
          {source === 'warehouse' ? (
            <span className="badge badge-warehouse" title="Ground truth historical observation from SQLite warehouse.db">
              <Database size={10} /> Real Warehouse
            </span>
          ) : (
            <span className="badge badge-simulation" title="Synthetic state evolved in memory by simulation engine">
              <Cpu size={10} /> Simulated
            </span>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.4rem', margin: '0.25rem 0' }}>
          <span className="mono-num" style={{ fontSize: '1.85rem', fontWeight: 700, color: color || '#f8fafc' }}>
            {value}
          </span>
          {unit && <span style={{ fontSize: '0.9rem', color: '#94a3b8', fontWeight: 500 }}>{unit}</span>}
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
        <span style={{ fontSize: '0.75rem', color: '#64748b' }}>{subtitle}</span>
        {trend && (
          <span
            style={{
              fontSize: '0.75rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.2rem',
              color: trend === 'up' ? '#38bdf8' : trend === 'down' ? '#f87171' : '#94a3b8',
            }}
          >
            {trend === 'up' && <TrendingUp size={12} />}
            {trend === 'down' && <TrendingDown size={12} />}
            {trend === 'neutral' && <Minus size={12} />}
            {trendLabel}
          </span>
        )}
      </div>
    </div>
  );
}
