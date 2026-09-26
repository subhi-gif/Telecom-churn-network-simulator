import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Database, Layers, ArrowDownRight, Scissors, Grid, AlertTriangle } from 'lucide-react';

export default function OLAPPanel() {
  const [olapTab, setOlapTab] = useState('customer'); // 'customer' or 'network'
  const [operation, setOperation] = useState('rollup'); // 'rollup', 'drilldown', 'slice', 'dice', 'high_drop'

  // Operation parameters
  const [rollupDim, setRollupDim] = useState('contract');
  const [drilldownBand, setDrilldownBand] = useState('0-12 months');
  const [sliceDim, setSliceDim] = useState('contract');
  const [sliceVal, setSliceVal] = useState('Month-to-month');

  // Network operation parameters
  const [netRollupLevel, setNetRollupLevel] = useState('region');
  const [netDrilldownRegion, setNetDrilldownRegion] = useState('Central');
  const [netSliceDim, setNetSliceDim] = useState('region');
  const [netSliceVal, setNetSliceVal] = useState('Central');

  const [resultData, setResultData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Execute active OLAP query
  useEffect(() => {
    async function executeOlap() {
      setLoading(true);
      setError(null);
      try {
        let res;
        if (olapTab === 'customer') {
          if (operation === 'rollup') res = await api.getOlapCustomerRollup(rollupDim);
          else if (operation === 'drilldown') res = await api.getOlapCustomerDrilldown(drilldownBand);
          else if (operation === 'slice') res = await api.getOlapCustomerSlice(sliceDim, sliceVal);
          else if (operation === 'dice') res = await api.getOlapCustomerDice({ contract: 'Month-to-month', internet_service: 'Fiber optic' });
        } else {
          if (operation === 'rollup') res = await api.getOlapNetworkRollup(netRollupLevel);
          else if (operation === 'drilldown') res = await api.getOlapNetworkDrilldown(netDrilldownRegion);
          else if (operation === 'slice') res = await api.getOlapNetworkSlice(netSliceDim, netSliceVal);
          else if (operation === 'dice') res = await api.getOlapNetworkDice({ region: 'Central', technology: '5G' });
          else if (operation === 'high_drop') res = await api.getOlapHighCallDrop(2.0);
        }

        if (res.success) {
          setResultData(res.data);
        } else {
          setError(res.error?.message || 'OLAP query failed.');
        }
      } catch (err) {
        setError('Error executing OLAP query.');
      } finally {
        setLoading(false);
      }
    }
    executeOlap();
  }, [
    olapTab,
    operation,
    rollupDim,
    drilldownBand,
    sliceDim,
    sliceVal,
    netRollupLevel,
    netDrilldownRegion,
    netSliceDim,
    netSliceVal,
  ]);

  const rows = Array.isArray(resultData?.results) ? resultData.results : resultData?.results ? [resultData.results] : [];
  const columns = rows.length > 0 ? Object.keys(rows[0]) : [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Header & Sub-mart switcher */}
      <div
        className="card"
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
          padding: '1rem 1.25rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Database size={20} color="#3b82f6" />
          <div>
            <div style={{ fontSize: '1rem', fontWeight: 700 }}>OLAP ANALYSIS</div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
              Multidimensional Aggregations (Star Schema Facts: <code>warehouse.db</code>)
            </div>
          </div>
          <span className="badge badge-warehouse">REAL WAREHOUSE DATA</span>
        </div>

        {/* Mart Switcher */}
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            className={`btn ${olapTab === 'customer' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => { setOlapTab('customer'); setOperation('rollup'); }}
          >
            Customer Churn Mart
          </button>
          <button
            className={`btn ${olapTab === 'network' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => { setOlapTab('network'); setOperation('rollup'); }}
          >
            Network Performance Mart
          </button>
        </div>
      </div>

      {/* Operation Tabs & Controls */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.75rem' }}>
          <button
            className={`tab-btn ${operation === 'rollup' ? 'active' : ''}`}
            onClick={() => setOperation('rollup')}
          >
            <Layers size={14} /> Roll-up
          </button>
          <button
            className={`tab-btn ${operation === 'drilldown' ? 'active' : ''}`}
            onClick={() => setOperation('drilldown')}
          >
            <ArrowDownRight size={14} /> Drill-down
          </button>
          <button
            className={`tab-btn ${operation === 'slice' ? 'active' : ''}`}
            onClick={() => setOperation('slice')}
          >
            <Scissors size={14} /> Slice
          </button>
          <button
            className={`tab-btn ${operation === 'dice' ? 'active' : ''}`}
            onClick={() => setOperation('dice')}
          >
            <Grid size={14} /> Dice
          </button>
          {olapTab === 'network' && (
            <button
              className={`tab-btn ${operation === 'high_drop' ? 'active' : ''}`}
              onClick={() => setOperation('high_drop')}
            >
              <AlertTriangle size={14} /> High Call Drop Analysis
            </button>
          )}
        </div>

        {/* Dynamic Parameter Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
          {olapTab === 'customer' && operation === 'rollup' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Roll-up Dimension:</span>
              <select className="select-input" value={rollupDim} onChange={(e) => setRollupDim(e.target.value)}>
                <option value="contract">Contract Type</option>
                <option value="internet_service">Internet Service</option>
                <option value="payment_method">Payment Method</option>
                <option value="tenure_band">Tenure Band</option>
              </select>
            </div>
          )}

          {olapTab === 'customer' && operation === 'drilldown' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Tenure Band:</span>
              <select className="select-input" value={drilldownBand} onChange={(e) => setDrilldownBand(e.target.value)}>
                <option value="0-12 months">0-12 months</option>
                <option value="13-24 months">13-24 months</option>
                <option value="25-48 months">25-48 months</option>
                <option value="49-72 months">49-72 months</option>
              </select>
            </div>
          )}

          {olapTab === 'customer' && operation === 'slice' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Slice Dimension:</span>
              <select className="select-input" value={sliceDim} onChange={(e) => setSliceDim(e.target.value)}>
                <option value="contract">Contract</option>
                <option value="internet_service">Internet Service</option>
                <option value="payment_method">Payment Method</option>
              </select>
              <input
                className="text-input"
                type="text"
                value={sliceVal}
                onChange={(e) => setSliceVal(e.target.value)}
                placeholder="Value..."
              />
            </div>
          )}

          {olapTab === 'network' && operation === 'rollup' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Level:</span>
              <select className="select-input" value={netRollupLevel} onChange={(e) => setNetRollupLevel(e.target.value)}>
                <option value="region">Region</option>
                <option value="technology">Technology</option>
                <option value="hour">Hour</option>
                <option value="minute">Minute</option>
              </select>
            </div>
          )}

          {olapTab === 'network' && operation === 'drilldown' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Region:</span>
              <select className="select-input" value={netDrilldownRegion} onChange={(e) => setNetDrilldownRegion(e.target.value)}>
                <option value="Central">Central</option>
                <option value="North">North</option>
                <option value="South">South</option>
                <option value="East">East</option>
                <option value="West">West</option>
              </select>
            </div>
          )}
        </div>
      </div>

      {loading && (
        <div className="loading-box">
          <div className="spinner" />
          <p>Executing parameterized OLAP query against star schema...</p>
        </div>
      )}

      {error && (
        <div className="alert-box alert-critical">
          <strong>Error:</strong> {error}
        </div>
      )}

      {!loading && (
        <div className="card">
          <div className="card-title">
            <span>Query Results: <code>{resultData?.operation}</code></span>
            <span style={{ fontSize: '0.8rem', color: '#64748b' }}>{rows.length} rows returned</span>
          </div>

          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  {columns.map((col) => (
                    <th key={col}>{col.replace(/_/g, ' ')}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, idx) => (
                  <tr key={idx}>
                    {columns.map((col) => (
                      <td key={col} className={typeof row[col] === 'number' ? 'mono-num' : ''}>
                        {typeof row[col] === 'number' ? row[col].toLocaleString() : String(row[col])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
