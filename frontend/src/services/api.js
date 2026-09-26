/**
 * Centralized API Service for Telecom Churn & Network Analysis Dashboard
 * Connects to the FastAPI backend service layer.
 */

const RAW_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';
const BASE_URL = RAW_URL ? RAW_URL.replace(/\/+$/, '') : '';

async function request(endpoint, options = {}) {
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const targetUrl = BASE_URL ? `${BASE_URL}${cleanEndpoint}` : cleanEndpoint;
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  try {
    let res;
    try {
      res = await fetch(targetUrl, config);
    } catch (directErr) {
      // If direct cross-origin fetch fails and BASE_URL was absolute, attempt relative Vite proxy as fallback
      if (BASE_URL && typeof window !== 'undefined' && window.location?.origin) {
        try {
          res = await fetch(cleanEndpoint, config);
        } catch {
          throw directErr;
        }
      } else {
        throw directErr;
      }
    }

    const json = await res.json();
    if (!res.ok) {
      const errorMsg = json?.error?.message || json?.detail || `HTTP ${res.status}: ${res.statusText}`;
      return { success: false, error: { code: json?.error?.code || 'API_ERROR', message: errorMsg } };
    }
    return json;
  } catch (err) {
    console.error(`[API Network Error] ${endpoint}:`, err);
    return {
      success: false,
      error: {
        code: 'NETWORK_ERROR',
        message: `Backend API unavailable at ${BASE_URL || 'current host'}. (${err.message || 'Failed to fetch'})`,
      },
    };
  }
}

export const api = {
  // 1. Health & Status
  getHealth: () => request('/api/health'),

  // 2. Cell Inventory
  getCells: (params = {}) => {
    const q = new URLSearchParams();
    if (params.region) q.append('region', params.region);
    if (params.technology) q.append('technology', params.technology);
    const qs = q.toString() ? `?${q.toString()}` : '';
    return request(`/api/cells${qs}`);
  },
  getCellDetail: (cellId) => request(`/api/cells/${encodeURIComponent(cellId)}`),

  // 3. Network KPI Telemetry
  getNetworkTelemetry: (cellId, params = {}) => {
    const q = new URLSearchParams();
    if (params.start_time) q.append('start_time', params.start_time);
    if (params.end_time) q.append('end_time', params.end_time);
    if (params.limit) q.append('limit', params.limit);
    const qs = q.toString() ? `?${q.toString()}` : '';
    return request(`/api/network/${encodeURIComponent(cellId)}${qs}`);
  },
  getNetworkSummary: (cellId) => request(`/api/network/${encodeURIComponent(cellId)}/summary`),

  // 4. Multidimensional OLAP Analysis
  getOlapCustomerSummary: () => request('/api/olap/customer/summary'),
  getOlapCustomerRollup: (groupBy = 'contract') => request(`/api/olap/customer/rollup?group_by=${encodeURIComponent(groupBy)}`),
  getOlapCustomerDrilldown: (tenureBand = '0-12 months') => request(`/api/olap/customer/drilldown?tenure_band=${encodeURIComponent(tenureBand)}`),
  getOlapCustomerSlice: (dimension, value) => request(`/api/olap/customer/slice?dimension=${encodeURIComponent(dimension)}&value=${encodeURIComponent(value)}`),
  getOlapCustomerDice: (filters = {}) => {
    const q = new URLSearchParams(filters);
    return request(`/api/olap/customer/dice?${q.toString()}`);
  },
  getOlapNetworkSummary: () => request('/api/olap/network/summary'),
  getOlapNetworkRollup: (level = 'hour') => request(`/api/olap/network/rollup?level=${encodeURIComponent(level)}`),
  getOlapNetworkDrilldown: (region, cellId = null) => {
    const q = new URLSearchParams({ region });
    if (cellId) q.append('cell_id', cellId);
    return request(`/api/olap/network/drilldown?${q.toString()}`);
  },
  getOlapNetworkSlice: (dimension, value) => request(`/api/olap/network/slice?dimension=${encodeURIComponent(dimension)}&value=${encodeURIComponent(value)}`),
  getOlapNetworkDice: (filters = {}) => {
    const q = new URLSearchParams(filters);
    return request(`/api/olap/network/dice?${q.toString()}`);
  },
  getOlapHighCallDrop: (threshold = 2.0) => request(`/api/olap/network/high-call-drop?threshold=${threshold}`),

  // 5. Data Mining & ML
  getMiningSummary: () => request('/api/mining/summary'),
  getMiningChurn: () => request('/api/mining/churn'),
  getMiningClusters: () => request('/api/mining/clusters'),
  getMiningAssociationRules: (params = {}) => {
    const q = new URLSearchParams();
    if (params.churn_only !== undefined) q.append('churn_only', params.churn_only);
    if (params.min_confidence) q.append('min_confidence', params.min_confidence);
    if (params.limit) q.append('limit', params.limit);
    const qs = q.toString() ? `?${q.toString()}` : '';
    return request(`/api/mining/association-rules${qs}`);
  },

  // 6. Network Simulation Engine
  getSimulationState: () => request('/api/simulation/state'),
  selectSimulationCell: (cellId) => request('/api/simulation/select-cell', {
    method: 'POST',
    body: JSON.stringify({ cell_id: cellId }),
  }),
  applySimulationScenario: (scenario, severity = 'MEDIUM') => request('/api/simulation/scenario', {
    method: 'POST',
    body: JSON.stringify({ scenario, severity }),
  }),
  updateSimulation: (deltaTime = 1.0) => request('/api/simulation/update', {
    method: 'POST',
    body: JSON.stringify({ delta_time: deltaTime }),
  }),
  pauseSimulation: () => request('/api/simulation/pause', { method: 'POST' }),
  resumeSimulation: () => request('/api/simulation/resume', { method: 'POST' }),
  resetSimulation: () => request('/api/simulation/reset', { method: 'POST' }),
  getSimulationComparison: () => request('/api/simulation/comparison'),
  getSimulationEvents: () => request('/api/simulation/events'),
  clearSimulationEvents: () => request('/api/simulation/events', { method: 'DELETE' }),
};
