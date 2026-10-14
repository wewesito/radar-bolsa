// Gráficos ligeros en SVG: línea de precio con lectura al pasar el ratón y minigráficos.

import { useMemo, useRef, useState } from "react";
import { fmtDate, fmtMoney, fmtPct } from "../format";

export function Sparkline({ values, tone }: { values: number[]; tone: "up" | "down" }) {
  if (values.length < 2) return <div style={{ height: 28 }} />;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const pts = values
    .map((v, i) => `${(i / (values.length - 1)) * 100},${26 - ((v - min) / (max - min || 1)) * 24}`)
    .join(" ");
  return (
    <svg aria-hidden="true" viewBox="0 0 100 28" preserveAspectRatio="none" style={{ width: "100%", height: 28, display: "block" }}>
      <polyline points={pts} fill="none" stroke={`var(--${tone === "up" ? "buy" : "avoid"})`} strokeWidth="2" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

const W = 800;
const H = 240;
const PAD = { top: 12, right: 64, bottom: 24, left: 8 };

export function PriceChart({ points, currency }: { points: [string, number][]; currency: string | null }) {
  const svg = useRef<SVGSVGElement>(null);
  const [hover, setHover] = useState<number | null>(null);

  const geo = useMemo(() => {
    const vals = points.map((p) => p[1]);
    const min = Math.min(...vals);
    const max = Math.max(...vals);
    const pad = (max - min) * 0.08 || max * 0.02;
    const lo = min - pad;
    const hi = max + pad;
    const x = (i: number) => PAD.left + (i / Math.max(points.length - 1, 1)) * (W - PAD.left - PAD.right);
    const y = (v: number) => PAD.top + (1 - (v - lo) / (hi - lo)) * (H - PAD.top - PAD.bottom);
    const path = points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p[1]).toFixed(1)}`).join("");
    const ticks = [0, 0.5, 1].map((f) => lo + (hi - lo) * f);
    return { x, y, path, ticks, lo, hi };
  }, [points]);

  if (points.length < 2) return <div className="empty">Sin histórico suficiente para dibujar el gráfico.</div>;

  const first = points[0][1];
  const last = points[points.length - 1][1];
  const change = last / first - 1;
  const hp = hover != null ? points[hover] : null;

  const onMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const r = svg.current!.getBoundingClientRect();
    const fx = ((e.clientX - r.left) / r.width) * W;
    const i = Math.round(((fx - PAD.left) / (W - PAD.left - PAD.right)) * (points.length - 1));
    setHover(Math.min(points.length - 1, Math.max(0, i)));
  };

  return (
    <div className="stack tight">
      <div className="row between small">
        <span className="muted">
          {hp ? fmtDate(hp[0]) : `${fmtDate(points[0][0])} – ${fmtDate(points[points.length - 1][0])}`}
        </span>
        <span className="strong">
          {hp ? fmtMoney(hp[1], currency) : <span className={change >= 0 ? "up" : "down"}>{fmtPct(change, 1, true)} en el periodo</span>}
        </span>
      </div>
      <svg
        ref={svg}
        role="img"
        aria-label={`Evolución del precio: ${fmtPct(change, 1, true)} en el periodo, de ${fmtMoney(first, currency)} a ${fmtMoney(last, currency)}`}
        viewBox={`0 0 ${W} ${H}`}
        style={{ width: "100%", height: "auto", display: "block" }}
        onMouseMove={onMove}
        onMouseLeave={() => setHover(null)}
      >
        {geo.ticks.map((t) => (
          <g key={t}>
            <line x1={PAD.left} x2={W - PAD.right} y1={geo.y(t)} y2={geo.y(t)} stroke="var(--border)" strokeDasharray="3 4" />
            <text x={W - PAD.right + 6} y={geo.y(t) + 4} fontSize="12" fill="var(--muted)">
              {fmtMoney(t, null)}
            </text>
          </g>
        ))}
        <path d={geo.path} fill="none" stroke="var(--chart)" strokeWidth="2.2" strokeLinejoin="round" />
        {hp && hover != null && (
          <g>
            <line x1={geo.x(hover)} x2={geo.x(hover)} y1={PAD.top} y2={H - PAD.bottom} stroke="var(--muted)" strokeWidth="1" />
            <circle cx={geo.x(hover)} cy={geo.y(hp[1])} r="4.5" fill="var(--chart)" stroke="var(--surface)" strokeWidth="2" />
          </g>
        )}
      </svg>
    </div>
  );
}
