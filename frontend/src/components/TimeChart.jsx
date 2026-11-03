import { useEffect, useRef, useState } from "react";
import { formatClock, valueAt } from "../lib/series.js";

const M = { left: 46, right: 14, top: 6, bottom: 22 };

function niceDomain(data, keys, fixed) {
  if (fixed) return fixed;
  const values = data.flatMap((d) => keys.map((k) => d[k])).filter((v) => v != null);
  if (!values.length) return [0, 1];
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const pad = (hi - lo || 1) * 0.12;
  return [lo - pad, hi + pad];
}

function path(data, key, x, y) {
  let d = "";
  let pen = false;
  for (const p of data) {
    if (p[key] == null) {
      pen = false;
      continue;
    }
    d += `${pen ? "L" : "M"}${x(p.t).toFixed(1)},${y(p[key]).toFixed(1)}`;
    pen = true;
  }
  return d;
}

// Jeden graf časového radu. Viac grafov zdieľa os x aj kurzor cez `hoverT`.
export default function TimeChart({
  title, unit, series, data, xDomain, yDomain, bands = [], markers = [],
  hoverT, onHover, height = 150, format = (v) => v.toFixed(0), showClock = false,
}) {
  const ref = useRef(null);
  const [width, setWidth] = useState(640);

  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(240, entry.contentRect.width)));
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const [x0, x1] = xDomain;
  const [y0, y1] = niceDomain(data, series.map((s) => s.key), yDomain);
  const x = (t) => M.left + ((t - x0) / (x1 - x0 || 1)) * (width - M.left - M.right);
  const y = (v) => M.top + (1 - (v - y0) / (y1 - y0 || 1)) * (height - M.top - M.bottom);
  const yTicks = [0, 1, 2, 3].map((i) => y0 + ((y1 - y0) * i) / 3);
  const xTicks = [0, 1, 2, 3, 4].map((i) => x0 + ((x1 - x0) * i) / 4);

  const move = (event) => {
    if (!onHover) return;
    const box = event.currentTarget.getBoundingClientRect();
    const px = event.clientX - box.left;
    const t = x0 + ((px - M.left) / (width - M.left - M.right)) * (x1 - x0);
    onHover(t >= x0 && t <= x1 ? t : null);
  };

  const live = hoverT == null;
  const shown = (key) => (live ? data[data.length - 1]?.[key] : valueAt(data, hoverT, key));

  return (
    <figure className="chart" ref={ref}>
      <figcaption className="chart-head">
        <span className="chart-title">{title}</span>
        <span className="chart-legend">
          {series.map((s) => (
            <span key={s.key} className="legend-item">
              <i style={{ background: s.color }} aria-hidden="true" />
              {s.label}
              <b>{shown(s.key) != null ? `${format(shown(s.key))}${unit}` : "–"}</b>
            </span>
          ))}
        </span>
      </figcaption>
      <svg
        width={width} height={height} role="img" aria-label={title}
        onMouseMove={move} onMouseLeave={() => onHover?.(null)}
      >
        {bands.map((b, i) => (
          <g key={`${b.phase}-${b.t0}`}>
            <rect
              x={x(Math.max(b.t0, x0))} y={M.top} height={height - M.top - M.bottom}
              width={Math.max(0, x(Math.min(b.t1, x1)) - x(Math.max(b.t0, x0)))}
              className={`band band-${i % 2}`}
            />
          </g>
        ))}
        {yTicks.map((v) => (
          <g key={v}>
            <line x1={M.left} x2={width - M.right} y1={y(v)} y2={y(v)} className="grid" />
            <text x={M.left - 6} y={y(v) + 4} textAnchor="end" className="tick">{format(v)}</text>
          </g>
        ))}
        {xTicks.map((t) => (
          <text key={t} x={x(t)} y={height - 6} textAnchor="middle" className="tick">
            {showClock ? formatClock(t) : t.toFixed(0)}
          </text>
        ))}
        {series.map((s) => (
          <path key={s.key} d={path(data, s.key, x, y)} fill="none" stroke={s.color} strokeWidth="2" strokeLinejoin="round" />
        ))}
        {markers.filter((m) => m.t >= x0 && m.t <= x1).map((m) => (
          <path key={m.t} d={`M${x(m.t) - 4},${height - M.bottom} l4,-7 l4,7 z`} className="marker">
            <title>{m.label}</title>
          </path>
        ))}
        {hoverT != null && <line x1={x(hoverT)} x2={x(hoverT)} y1={M.top} y2={height - M.bottom} className="cursor" />}
      </svg>
    </figure>
  );
}
