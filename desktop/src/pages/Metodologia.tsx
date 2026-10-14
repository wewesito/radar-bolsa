import { useEffect } from "react";
import { api, invalidate, useApi } from "../api";
import { ErrorBox, Loading, Stamp } from "../components/ui";
import { fmtDate, fmtNum, fmtPct } from "../format";
import type { BacktestResult, BacktestState } from "../types";

const W = 760;
const H = 300;
const PAD = { top: 12, right: 12, bottom: 24, left: 46 };

// Cada serie lleva color Y trazo distinto: no se distingue solo por color.
const STYLES: { color: string; dash?: string; width: number }[] = [
  { color: "var(--chart)", width: 2.6 },
  { color: "var(--muted)", dash: "6 4", width: 1.8 },
  { color: "var(--watch)", dash: "2 3", width: 1.8 },
  { color: "var(--buy)", dash: "10 3 2 3", width: 1.8 },
];

function BacktestChart({ res }: { res: BacktestResult }) {
  const names = Object.keys(res.series);
  const all = names.flatMap((n) => res.series[n].filter((v): v is number => v != null));
  const lo = Math.min(...all) * 0.95;
  const hi = Math.max(...all) * 1.05;
  const n = res.dates.length;
  const x = (i: number) => PAD.left + (i / Math.max(n - 1, 1)) * (W - PAD.left - PAD.right);
  const y = (v: number) => PAD.top + (1 - (v - lo) / (hi - lo)) * (H - PAD.top - PAD.bottom);
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => lo + (hi - lo) * f);
  const xt = [0, Math.floor(n / 3), Math.floor((2 * n) / 3), n - 1];
  const path = (vals: (number | null)[]) =>
    vals
      .map((v, i) => (v == null ? "" : `${i === 0 || vals[i - 1] == null ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`))
      .join("");
  const summary = names.map((nm) => `${nm}: ${fmtNum(res.series[nm].at(-1) ?? null, 0)}`).join("; ");
  return (
    <div className="stack tight">
      <svg role="img" aria-label={`Evolución de 100 € invertidos. ${summary}`} viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "auto" }}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)} stroke="var(--border)" />
            <text x={PAD.left - 6} y={y(t) + 4} textAnchor="end" fontSize="11" fill="var(--muted)">{fmtNum(t, 0)}</text>
          </g>
        ))}
        {xt.map((i) => (
          <text key={i} x={x(i)} y={H - 6} textAnchor={i === 0 ? "start" : i === n - 1 ? "end" : "middle"} fontSize="11" fill="var(--muted)">
            {fmtDate(res.dates[i])}
          </text>
        ))}
        {names.map((nm, k) => {
          const st = STYLES[k % STYLES.length];
          return <path key={nm} d={path(res.series[nm])} fill="none" stroke={st.color} strokeWidth={st.width} strokeDasharray={st.dash} strokeLinejoin="round" />;
        })}
      </svg>
      <div className="row wrap small" aria-label="Leyenda">
        {names.map((nm, k) => {
          const st = STYLES[k % STYLES.length];
          return (
            <span key={nm} className="row" style={{ gap: 6 }}>
              <svg width="28" height="8" aria-hidden="true"><line x1="0" x2="28" y1="4" y2="4" stroke={st.color} strokeWidth={st.width} strokeDasharray={st.dash} /></svg>
              {nm}
            </span>
          );
        })}
      </div>
    </div>
  );
}

function Results({ res }: { res: BacktestResult }) {
  const names = Object.keys(res.series);
  const years = Object.keys(res.yearly);
  return (
    <>
      <section className="card stack">
        <h2>Evolución de 100 € (en euros, con dividendos)</h2>
        <BacktestChart res={res} />
        <Stamp source={res.source} at={res.built_at} prefix="Calculado:" />
      </section>
      <section className="card stack">
        <h2>Resumen</h2>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr><th>Cartera</th><th>Total</th><th>Anualizada</th><th>Volatilidad</th><th>Peor caída</th><th>Rent./riesgo</th></tr>
            </thead>
            <tbody>
              {names.map((nm) => {
                const m = res.metrics[nm];
                return (
                  <tr key={nm}>
                    <td className="strong">{nm}</td>
                    <td>{fmtPct(m.total_return, 1, true)}</td>
                    <td>{fmtPct(m.cagr, 1, true)}</td>
                    <td>{fmtPct(m.volatility, 1)}</td>
                    <td>{fmtPct(m.max_drawdown, 1)}</td>
                    <td>{fmtNum(m.return_per_risk, 2)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
      <section className="card stack">
        <h2>Año a año</h2>
        <div className="table-wrap">
          <table className="data">
            <thead><tr><th>Año</th>{names.map((nm) => <th key={nm}>{nm}</th>)}</tr></thead>
            <tbody>
              {years.map((y) => (
                <tr key={y}>
                  <td className="strong">{y}</td>
                  {names.map((nm) => <td key={nm}>{fmtPct(res.yearly[y][nm] ?? null, 1, true)}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="tiny muted">El primer y el último año pueden ser parciales.</p>
      </section>
    </>
  );
}

export function Metodologia() {
  const bt = useApi<BacktestState>("/api/backtest");
  const docs = useApi<Record<string, string>>("/api/methodology");
  const running = bt.data?.running;

  // Mientras se calcula, se consulta el estado cada pocos segundos.
  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => { invalidate("/api/backtest"); }, 4000);
    return () => clearInterval(id);
  }, [running]);

  const run = async () => {
    await api("/api/backtest/run", { method: "POST" }).catch(() => undefined);
    invalidate("/api/backtest");
  };

  return (
    <div className="stack" style={{ gap: 20, maxWidth: 920 }}>
      <h1>Metodología y backtest</h1>
      <p className="muted" style={{ lineHeight: 1.55 }}>
        Aquí ves cómo se calcula la señal y qué habría pasado con el modelo en el pasado. Un buen resultado pasado no garantiza nada futuro.
      </p>

      <section className="card stack">
        <h2>Backtest de la parte de precio</h2>
        <p className="small muted" style={{ lineHeight: 1.55 }}>
          Se recalcula la puntuación de precio (momentum y riesgo) cada trimestre usando solo los datos conocidos hasta ese día, se compran las 20 mejores a partes iguales y se compara con el universo entero y con dos índices. Coste supuesto: 0,1 % por euro negociado.
        </p>
        <div className="error-box small" style={{ lineHeight: 1.5 }}>
          <strong>Límites que debes conocer.</strong> Solo se prueba la parte de precio: valoración, salud, crecimiento y dividendo no se pueden probar porque Yahoo solo da los fundamentales de hoy (usarlos en el pasado sería mirar al futuro). Además hay <strong>sesgo de supervivencia</strong>: el universo son las empresas que cotizan hoy, sin las que quebraron o dejaron de cotizar. Por eso se compara con el universo entero, que tiene el mismo sesgo: la diferencia mide lo que aporta la selección. El IBEX 35 con dividendos se aproxima con un ETF.
        </div>
        <div className="row wrap">
          <button className="btn primary" onClick={run} disabled={running}>
            {running ? "Calculando… (puede tardar unos minutos)" : bt.data?.result ? "Recalcular" : "Calcular backtest"}
          </button>
          {running && <span className="small muted" aria-live="polite">Descargando 10 años de histórico semanal.</span>}
        </div>
        {bt.data?.error && <div className="error-box small">{bt.data.error}</div>}
        {bt.error && <ErrorBox error={bt.error} onRetry={bt.reload} />}
      </section>

      {!bt.data && !bt.error && <Loading height={200} />}
      {bt.data?.result && <Results res={bt.data.result} />}
      {bt.data?.result && bt.data.result.failed.length > 0 && (
        <p className="tiny muted">Sin histórico suficiente y excluidos: {bt.data.result.failed.join(", ")}.</p>
      )}

      <section className="card stack">
        <h2>Reglas del modelo</h2>
        {!docs.data && !docs.error && <Loading height={80} />}
        {docs.error && <ErrorBox error={docs.error} onRetry={docs.reload} />}
        {docs.data && (
          [["Puntuación (0–100)", "score"], ["Señal Comprar / Vigilar / Evitar", "signal"], ["Perfil inversor", "profile"], ["Backtest", "backtest"]] as const
        ).map(([title, key]) => (
          <details key={key}>
            <summary className="strong" style={{ cursor: "pointer" }}>{title}</summary>
            <pre className="small" style={{ whiteSpace: "pre-wrap", lineHeight: 1.5, fontFamily: "inherit", marginTop: 8 }}>{docs.data?.[key]}</pre>
          </details>
        ))}
      </section>
    </div>
  );
}
