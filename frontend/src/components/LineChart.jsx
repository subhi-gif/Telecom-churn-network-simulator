import React, { useState } from 'react';

/**
 * Pure SVG Responsive Line Chart with Area Gradient and Tooltips
 * Zero external dependencies.
 */
export default function LineChart({
  data = [],
  xKey = 'timestamp',
  yKey = 'value',
  label = 'Metric',
  unit = '',
  strokeColor = '#06b6d4',
  height = 180,
}) {
  const [hoveredIndex, setHoveredIndex] = useState(null);

  if (!data || data.length === 0) {
    return (
      <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b' }}>
        No telemetry observations available
      </div>
    );
  }

  const values = data.map((d) => Number(d[yKey]) || 0);
  const rawMin = Math.min(...values);
  const rawMax = Math.max(...values);
  const range = rawMax - rawMin || 1.0;
  const padding = range * 0.15;
  const minY = Math.max(0, rawMin - padding);
  const maxY = rawMax + padding;

  const width = 600;
  const chartHeight = height - 40;
  const marginLeft = 45;
  const marginRight = 15;
  const marginTop = 10;
  const plotWidth = width - marginLeft - marginRight;
  const plotHeight = chartHeight - marginTop;

  const points = data.map((d, i) => {
    const x = marginLeft + (i / Math.max(1, data.length - 1)) * plotWidth;
    const yVal = Number(d[yKey]) || 0;
    const y = marginTop + plotHeight - ((yVal - minY) / (maxY - minY)) * plotHeight;
    return { x, y, val: yVal, item: d };
  });

  const pathD = points.reduce((acc, p, i) => (i === 0 ? `M ${p.x},${p.y}` : `${acc} L ${p.x},${p.y}`), '');
  const areaD = `${pathD} L ${points[points.length - 1].x},${marginTop + plotHeight} L ${points[0].x},${marginTop + plotHeight} Z`;

  // Grid tick marks
  const yTicks = [
    { val: minY, y: marginTop + plotHeight },
    { val: (minY + maxY) / 2, y: marginTop + plotHeight / 2 },
    { val: maxY, y: marginTop },
  ];

  const activePoint = hoveredIndex !== null ? points[hoveredIndex] : null;

  return (
    <div style={{ width: '100%', position: 'relative' }}>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        style={{ width: '100%', height: 'auto', overflow: 'visible' }}
        onMouseLeave={() => setHoveredIndex(null)}
      >
        <defs>
          <linearGradient id={`gradient-${label}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={strokeColor} stopOpacity="0.3" />
            <stop offset="100%" stopColor={strokeColor} stopOpacity="0.0" />
          </linearGradient>
        </defs>

        {/* Y Gridlines and Labels */}
        {yTicks.map((t, idx) => (
          <g key={idx}>
            <line
              x1={marginLeft}
              y1={t.y}
              x2={width - marginRight}
              y2={t.y}
              stroke="rgba(255, 255, 255, 0.08)"
              strokeDasharray="3 3"
            />
            <text
              x={marginLeft - 8}
              y={t.y + 4}
              fill="#64748b"
              fontSize="10"
              fontFamily="var(--font-mono)"
              textAnchor="end"
            >
              {t.val.toFixed(1)}
            </text>
          </g>
        ))}

        {/* Area and Line Path */}
        <path d={areaD} fill={`url(#gradient-${label})`} />
        <path d={pathD} fill="none" stroke={strokeColor} strokeWidth="2.2" strokeLinecap="round" />

        {/* Data points & Interaction Hitboxes */}
        {points.map((p, i) => (
          <g key={i}>
            <circle
              cx={p.x}
              cy={p.y}
              r={hoveredIndex === i ? 4.5 : 2}
              fill={hoveredIndex === i ? '#ffffff' : strokeColor}
              stroke={strokeColor}
              strokeWidth="1.5"
            />
            <rect
              x={p.x - plotWidth / (data.length * 2)}
              y={0}
              width={plotWidth / Math.max(1, data.length)}
              height={height}
              fill="transparent"
              style={{ cursor: 'pointer' }}
              onMouseEnter={() => setHoveredIndex(i)}
            />
          </g>
        ))}

        {/* Tooltip Overlay */}
        {activePoint && (
          <g>
            <line
              x1={activePoint.x}
              y1={marginTop}
              x2={activePoint.x}
              y2={marginTop + plotHeight}
              stroke="rgba(255, 255, 255, 0.3)"
              strokeDasharray="2 2"
            />
            <circle cx={activePoint.x} cy={activePoint.y} r="5" fill="#fff" stroke={strokeColor} strokeWidth="2" />
          </g>
        )}
      </svg>

      {/* Floating HTML Tooltip */}
      {activePoint && (
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: `${(activePoint.x / width) * 100}%`,
            transform: 'translateX(-50%)',
            background: 'rgba(15, 23, 42, 0.95)',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            padding: '4px 8px',
            borderRadius: '4px',
            fontSize: '11px',
            fontFamily: 'var(--font-mono)',
            color: '#fff',
            pointerEvents: 'none',
            whiteSpace: 'nowrap',
            zIndex: 10,
            boxShadow: '0 4px 6px rgba(0,0,0,0.5)',
          }}
        >
          <div>{label}: <strong>{activePoint.val.toFixed(2)} {unit}</strong></div>
          <div style={{ color: '#94a3b8', fontSize: '10px' }}>{activePoint.item[xKey]}</div>
        </div>
      )}
    </div>
  );
}
