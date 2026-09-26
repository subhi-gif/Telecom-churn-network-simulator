import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import LineChart from './LineChart';
import { Database, Filter, Wifi, Radio, Clock, BarChart } from 'lucide-react';

export default function NetworkOverview() {
  const [cells, setCells] = useState([]);
  const [selectedRegion, setSelectedRegion] = useState('');
  const [selectedTech, setSelectedTech] = useState('');
  const [selectedCellId, setSelectedCellId] = useState('Cell_0025');

  const [cellDetail, setCellDetail] = useState(null);
  const [summary, setSummary] = useState(null);
  const [telemetry, setTelemetry] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // 1. Load cells on mount
  useEffect(() => {
    async function loadCellList() {
      try {
        const res = await api.getCells();
        if (res.success && res.data.length > 0) {
          setCells(res.data);
          // Check if Cell_0025 exists
          const has0025 = res.data.some((c) => c.cell_id === 'Cell_0025');
          const target = has0025 ? 'Cell_0025' : res.data[0].cell_id;
          setSelectedCellId(target);
        }
      } catch (err) {
        setError('Failed to fetch cells from warehouse API.');
      }
    }
    loadCellList();
  }, []);

  // 2. Fetch cell telemetry whenever selectedCellId changes
  useEffect(() => {
    if (!selectedCellId) return;

    async function fetchCellData() {
      setLoading(true);
      setError(null);
      try {
        const [detailRes, summaryRes, telRes] = await Promise.all([
          api.getCellDetail(selectedCellId),
          api.getNetworkSummary(selectedCellId),
          api.getNetworkTelemetry(selectedCellId, { limit: 100 }),
        ]);

        if (detailRes.success && summaryRes.success && telRes.success) {
          setCellDetail(detailRes.data);
          setSummary(summaryRes.data);
          setTelemetry(telRes.data);
        } else {
          setError(detailRes.error?.message || summaryRes.error?.message || 'Error loading cell telemetry.');
        }
      } catch (err) {
        setError('Error loading network telemetry.');
      } finally {
        setLoading(false);
      }
    }
    fetchCellData();
  }, [selectedCellId]);

  // Derived filter options
  const regions = Array.from(new Set(cells.map((c) => c.region))).filter(Boolean).sort();
  const technologies = Array.from(new Set(cells.map((c) => c.technology))).filter(Boolean).sort();

  const filteredCells = cells.filter((c) => {
    if (selectedRegion && c.region !== selectedRegion) return false;
    if (selectedTech && c.technology !== selectedTech) return false;
    return true;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Real Warehouse Data Label & Selector Toolbar */}
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
          <Radio size={20} color="#06b6d4" />
          <div>
            <div style={{ fontSize: '0.95rem', fontWeight: 600 }}>Cell Sector Telemetry Explorer</div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
              Historical performance telemetry from <code>FACT_NETWORK_KPI</code>
            </div>
          </div>
          <span className="badge badge-warehouse">REAL WAREHOUSE DATA</span>
        </div>

        {/* Filter Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Region:</span>
            <select
              className="select-input"
              value={selectedRegion}
              onChange={(e) => setSelectedRegion(e.target.value)}
            >
              <option value="">All Regions</option>
              {regions.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Tech:</span>
            <select
              className="select-input"
              value={selectedTech}
              onChange={(e) => setSelectedTech(e.target.value)}
            >
              <option value="">All Techs</option>
              {technologies.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: 600 }}>Cell Sector:</span>
            <select
              className="select-input"
              value={selectedCellId}
              onChange={(e) => setSelectedCellId(e.target.value)}
              style={{ minWidth: '130px', borderColor: '#06b6d4', fontWeight: 600 }}
            >
              {filteredCells.map((c) => (
                <option key={c.cell_id} value={c.cell_id}>
                  {c.cell_id} ({c.technology} - {c.region})
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {loading && (
        <div className="loading-box">
          <div className="spinner" />
          <p>Querying time-series observations for {selectedCellId}...</p>
        </div>
      )}

      {error && (
        <div className="alert-box alert-critical">
          <strong>Error:</strong> {error}
        </div>
      )}

      {!loading && cellDetail && summary && (
        <>
          {/* Cell Metadata & Aggregate KPI Row */}
          <div className="grid-cols-4">
            <div className="card">
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Sector Identity</div>
              <div className="mono-num" style={{ fontSize: '1.4rem', fontWeight: 700, color: '#38bdf8' }}>
                {cellDetail.cell_id}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.25rem' }}>
                {cellDetail.region} Region • {cellDetail.technology}
              </div>
            </div>

            <div className="card">
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Avg Latency</div>
              <div className="mono-num" style={{ fontSize: '1.4rem', fontWeight: 700, color: '#34d399' }}>
                {summary.average_latency_ms} <span style={{ fontSize: '0.9rem' }}>ms</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.25rem' }}>
                Range: [{summary.metrics.latency_ms.min} - {summary.metrics.latency_ms.max} ms]
              </div>
            </div>

            <div className="card">
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Avg Downlink Throughput</div>
              <div className="mono-num" style={{ fontSize: '1.4rem', fontWeight: 700, color: '#38bdf8' }}>
                {summary.average_throughput_mbps} <span style={{ fontSize: '0.9rem' }}>Mbps</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.25rem' }}>
                Range: [{summary.metrics.throughput_mbps.min} - {summary.metrics.throughput_mbps.max} Mbps]
              </div>
            </div>

            <div className="card">
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Avg Call Drop Rate</div>
              <div className="mono-num" style={{ fontSize: '1.4rem', fontWeight: 700, color: summary.average_call_drop_rate_pct > 2 ? '#f87171' : '#34d399' }}>
                {summary.average_call_drop_rate_pct} <span style={{ fontSize: '0.9rem' }}>%</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.25rem' }}>
                Nominal floor (&lt; 2.0%)
              </div>
            </div>
          </div>

          {/* Time Series Charts Grid */}
          <div className="grid-cols-2">
            <div className="card">
              <div className="card-title">
                <span>Latency Over Time (ms)</span>
                <span className="badge badge-warehouse">FACT_NETWORK_KPI</span>
              </div>
              <LineChart
                data={telemetry}
                xKey="timestamp"
                yKey="latency_ms"
                label="Latency"
                unit="ms"
                strokeColor="#38bdf8"
                height={170}
              />
            </div>

            <div className="card">
              <div className="card-title">
                <span>Downlink Throughput (Mbps)</span>
                <span className="badge badge-warehouse">FACT_NETWORK_KPI</span>
              </div>
              <LineChart
                data={telemetry}
                xKey="timestamp"
                yKey="throughput_mbps"
                label="Throughput"
                unit="Mbps"
                strokeColor="#10b981"
                height={170}
              />
            </div>

            <div className="card">
              <div className="card-title">
                <span>Call Drop Rate (%)</span>
                <span className="badge badge-warehouse">FACT_NETWORK_KPI</span>
              </div>
              <LineChart
                data={telemetry}
                xKey="timestamp"
                yKey="call_drop_rate_pct"
                label="Drop Rate"
                unit="%"
                strokeColor="#f59e0b"
                height={170}
              />
            </div>

            <div className="card">
              <div className="card-title">
                <span>Packet Loss (%)</span>
                <span className="badge badge-warehouse">FACT_NETWORK_KPI</span>
              </div>
              <LineChart
                data={telemetry}
                xKey="timestamp"
                yKey="packet_loss_pct"
                label="Packet Loss"
                unit="%"
                strokeColor="#a855f7"
                height={170}
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
