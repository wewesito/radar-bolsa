import { useState } from "react";
import { api, invalidate, useApi } from "../api";
import { ErrorBox, Help, LabelPill, Loading, Stamp } from "../components/ui";
import { fmtDate, fmtMoney, fmtNum, fmtPct } from "../format";
import type { PortfolioData, TradeRow } from "../types";

const W = 760, H = 280, PAD = { t: 12, r: 12, b: 24, l: 56 };

function PortfolioChart({ c }: { c: NonNullable<PortfolioData["chart"]> }) {
  // Cada serie lleva color y trazo distintos: no se distinguen solo por color.
  const series = [
    { name: "Tu cartera", v: c.value, color: "var(--chart)", dash: undefined, w: 2.6 },
    { name: `Mismo dinero en ${c.benchmark_name.split(" (")[0]}`, v: c.benchmark, color: "var(--watch)", dash: "2 3", w: 2 },
    { name: "Dinero aportado", v: c.contributed, color: "var(--muted)", dash: "6 4", w: 1.8 },
  ];
  const all: number[] = series.flatMap((s) => (s.v as (number | null)[]).filter((x): x is number => x != null));
  const hi = Math.max(...all, 1) * 1.05;
  const lo = Math.min(...all, 0) * 0.95;
  const n = c.dates.length;
  const x = (i: number) => PAD.l + (i / Math.max(n - 1, 1)) * (W - PAD.l - PAD.r);
  const y = (v: number) => PAD.t + (1 - (v - lo) / (hi - lo)) * (H - PAD.t - PAD.b);
  const path = (vals: (number | null)[]) => vals.map((v, i) => (v == null ? "" : `${i === 0 || vals[i - 1] == null ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`)).join("");
  return (
    <div className="stack tight">
      <svg role="img" aria-label={`Evolución en euros. Tu cartera: ${fmtMoney(c.value.at(-1) ?? null, "EUR")}; ${series[1].name}: ${fmtMoney(c.benchmark.at(-1) ?? null, "EUR")}; aportado: ${fmtMoney(c.contributed.at(-1) ?? null, "EUR")}`} viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "auto" }}>
        {[0, 0.5, 1].map((f) => {
          const t = lo + (hi - lo) * f;
          return (
            <g key={f}>
              <line x1={PAD.l} x2={W - PAD.r} y1={y(t)} y2={y(t)} stroke="var(--border)" />
              <text x={PAD.l - 6} y={y(t) + 4} textAnchor="end" fontSize="11" fill="var(--muted)">{fmtNum(t, 0)}</text>
            </g>
          );
        })}
        <text x={PAD.l} y={H - 6} fontSize="11" fill="var(--muted)">{fmtDate(c.dates[0])}</text>
        <text x={W - PAD.r} y={H - 6} textAnchor="end" fontSize="11" fill="var(--muted)">{fmtDate(c.dates[n - 1])}</text>
        {series.map((s) => <path key={s.name} d={path(s.v)} fill="none" stroke={s.color} strokeWidth={s.w} strokeDasharray={s.dash} strokeLinejoin="round" />)}
      </svg>
      <div className="row wrap small">
        {series.map((s) => (
          <span key={s.name} className="row" style={{ gap: 6 }}>
            <svg width="28" height="8" aria-hidden="true"><line x1="0" x2="28" y1="4" y2="4" stroke={s.color} strokeWidth={s.w} strokeDasharray={s.dash} /></svg>
            {s.name} (€)
          </span>
        ))}
      </div>
    </div>
  );
}

function Bars({ title, data }: { title: string; data: Record<string, number> }) {
  return (
    <div className="stack tight">
      <h3>{title}</h3>
      {Object.entries(data).map(([k, v]) => (
        <div key={k} className="row" style={{ gap: 10 }}>
          <span className="small" style={{ flex: "0 0 150px" }}>{k}</span>
          <div className="progress" style={{ flex: 1 }} aria-hidden="true"><div style={{ width: `${v * 100}%` }} /></div>
          <span className="small strong" style={{ flex: "0 0 52px", textAlign: "right" }}>{fmtPct(v, 0)}</span>
        </div>
      ))}
    </div>
  );
}

export const inputStyle = { height: 42, borderRadius: 10, border: "1px solid var(--border)", background: "var(--surface2)", color: "var(--text)", padding: "0 12px", font: "inherit", width: "100%" } as const;
const today = () => new Date().toISOString().slice(0, 10);

function Fld({ label, basis = 140, children }: { label: string; basis?: number; children: React.ReactNode }) {
  return <label className="stack tight" style={{ flex: `1 1 ${basis}px` }}><span className="small strong">{label}</span>{children}</label>;
}

function TradeForm({ onDone }: { onDone: () => void }) {
  const [f, setF] = useState({ ticker: "", side: "BUY", quantity: "", price: "", fee: "0", date: today(), note: "" });
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF((o) => ({ ...o, [k]: e.target.value }));
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setMsg(null);
    try {
      await api("/api/portfolio/trades", {
        method: "POST",
        body: JSON.stringify({ ticker: f.ticker, side: f.side, quantity: Number(f.quantity), price: f.price ? Number(f.price) : null, fee: Number(f.fee || 0), date: f.date, note: f.note || null }),
      });
      setF((o) => ({ ...o, ticker: "", quantity: "", price: "", fee: "0", note: "" }));
      invalidate("/api/portfolio");
      onDone();
    } catch (err) {
      setMsg((err as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <form className="stack" onSubmit={submit}>
      <div className="row wrap" style={{ alignItems: "flex-end" }}>
        <Fld label="Ticker (p. ej. IBE.MC)"><input style={inputStyle} value={f.ticker} onChange={set("ticker")} required /></Fld>
        <Fld label="Operación" basis={110}><select style={inputStyle} value={f.side} onChange={set("side")}><option value="BUY">Compra</option><option value="SELL">Venta</option></select></Fld>
        <Fld label="Cantidad" basis={110}><input style={inputStyle} type="number" min="0" step="any" value={f.quantity} onChange={set("quantity")} required /></Fld>
        <Fld label="Precio (vacío = cierre del día)" basis={170}><input style={inputStyle} type="number" min="0" step="any" value={f.price} onChange={set("price")} /></Fld>
      </div>
      <div className="row wrap" style={{ alignItems: "flex-end" }}>
        <Fld label="Comisión" basis={110}><input style={inputStyle} type="number" min="0" step="any" value={f.fee} onChange={set("fee")} /></Fld>
        <Fld label="Fecha" basis={150}><input style={inputStyle} type="date" max={today()} value={f.date} onChange={set("date")} required /></Fld>
        <Fld label="Motivo (opcional)" basis={260}><input style={inputStyle} maxLength={300} value={f.note} onChange={set("note")} placeholder="¿Por qué haces esta operación?" /></Fld>
        <button className="btn primary" type="submit" disabled={busy || !f.ticker || !f.quantity}>{busy ? "Registrando…" : "Registrar"}</button>
      </div>
      {msg && <div className="error-box small" role="alert">{msg}</div>}
    </form>
  );
}

const tone = (x: number | null | undefined) => ((x ?? 0) >= 0 ? "up" : "down");
const arrow = (x: number | null | undefined) => ((x ?? 0) >= 0 ? "▲" : "▼");

export function Cartera() {
  const [bench, setBench] = useState("EUNL.DE");
  const pf = useApi<PortfolioData>(`/api/portfolio?bench=${encodeURIComponent(bench)}`);
  const trades = useApi<TradeRow[]>("/api/portfolio/trades");
  const [delError, setDelError] = useState<string | null>(null);
  const del = async (id: number) => {
    setDelError(null);
    try {
      await api(`/api/portfolio/trades/${id}`, { method: "DELETE" });
      invalidate("/api/portfolio");
    } catch (e) {
      setDelError((e as Error).message);
    }
  };
  const d = pf.data;
  const s = d?.summary;
  return (
    <div className="stack" style={{ gap: 20 }}>
      <div>
        <h1>Mi cartera</h1>
        <p className="muted" style={{ marginTop: 6, lineHeight: 1.55 }}>
          Todas las operaciones son <strong>ficticias</strong>: la app no se conecta a ningún bróker ni mueve dinero. Sirve para practicar y medir tus decisiones sin arriesgar nada.
        </p>
      </div>

      <section className="card stack">
        <h2>Registrar operación</h2>
        <TradeForm onDone={() => { trades.reload(); pf.reload(); }} />
      </section>

      {pf.error && <ErrorBox error={pf.error} onRetry={pf.reload} />}
      {!d && !pf.error && <Loading height={160} count={2} />}
      {d && d.trade_count === 0 && <div className="empty">Aún no hay operaciones. Registra tu primera compra ficticia arriba.</div>}

      {d && s && d.trade_count > 0 && (
        <>
          <section aria-label="Resumen" className="grid tiles">
            <div className="card stack tight"><span className="small strong muted">Valor actual</span><span style={{ fontSize: 23, fontWeight: 800 }}>{fmtMoney(s.market_value_eur, "EUR")}</span></div>
            <div className="card stack tight"><span className="small strong muted">Ganancia latente</span><span className={`strong ${tone(s.unrealized_eur)}`} style={{ fontSize: 23 }}>{arrow(s.unrealized_eur)} {fmtMoney(s.unrealized_eur, "EUR")}</span><span className="tiny muted">Valor − coste FIFO</span></div>
            <div className="card stack tight"><span className="small strong muted">Ganancia realizada</span><span className={`strong ${tone(s.realized_eur)}`} style={{ fontSize: 23 }}>{arrow(s.realized_eur)} {fmtMoney(s.realized_eur, "EUR")}</span><span className="tiny muted">De las ventas hechas</span></div>
            <div className="card stack tight"><span className="small strong muted row" style={{ gap: 6 }}>Rentabilidad total <Help term="portfolio_return" /></span><span className={`strong ${tone(s.total_return)}`} style={{ fontSize: 23 }}>{arrow(s.total_return)} {fmtPct(s.total_return, 2, true)}</span></div>
          </section>
          <Stamp source={d.source} at={d.as_of} delay={15} prefix="Valorado con precios de" />
          {d.failed.length > 0 && <div className="error-box small">Sin precio actual para: {d.failed.join(", ")}.</div>}

          <section className="card stack">
            <div className="row between wrap">
              <h2 className="row" style={{ gap: 6 }}>Comparación con un índice <Help term="shadow_portfolio" /></h2>
              <label className="row small" style={{ gap: 8 }}>
                Índice
                <select value={bench} onChange={(e) => setBench(e.target.value)} style={{ ...inputStyle, width: "auto", height: 36 }}>
                  {d.benchmarks.map((b) => <option key={b.ticker} value={b.ticker}>{b.name}</option>)}
                </select>
              </label>
            </div>
            {d.chart ? (
              <>
                <PortfolioChart c={d.chart} />
                {(() => {
                  const mine = d.chart.value.at(-1) ?? 0;
                  const ref = d.chart.benchmark.at(-1);
                  if (ref == null) return null;
                  const diff = mine - ref;
                  return <p className="small" aria-live="polite">Con el mismo dinero y las mismas fechas, el índice valdría <strong>{fmtMoney(ref, "EUR")}</strong>: tu cartera va {diff >= 0 ? "por encima" : "por debajo"} por <strong>{fmtMoney(Math.abs(diff), "EUR")}</strong>.</p>;
                })()}
              </>
            ) : <p className="muted small">No hay histórico suficiente para dibujar la evolución todavía.</p>}
          </section>

          <section className="card stack">
            <h2>Posiciones abiertas</h2>
            {d.positions.length === 0 ? <p className="muted small">No tienes posiciones abiertas (todo vendido).</p> : (
              <div className="table-wrap">
                <table className="data">
                  <thead><tr><th>Valor</th><th>Señal del modelo</th><th>Cantidad</th><th>Precio medio</th><th>Precio actual</th><th>Valor (€)</th><th>Ganancia (€)</th><th>%</th><th>Peso</th></tr></thead>
                  <tbody>
                    {d.positions.map((p) => (
                      <tr key={p.ticker}>
                        <td><a href={`#/detalle/${encodeURIComponent(p.ticker)}`}><span className="strong">{p.name}</span></a> <span className="tiny muted">{p.ticker}</span></td>
                        <td>{p.label ? <LabelPill label={p.label} /> : <span className="muted small">n/d</span>}</td>
                        <td>{fmtNum(p.quantity, 2)}</td>
                        <td>{fmtMoney(p.avg_price, p.currency)}</td>
                        <td>{fmtMoney(p.price, p.currency)}</td>
                        <td>{fmtMoney(p.value_eur, "EUR")}</td>
                        <td className={tone(p.pnl_eur)}>{arrow(p.pnl_eur)} {fmtMoney(p.pnl_eur, "EUR")}</td>
                        <td className={tone(p.pnl_pct)}>{fmtPct(p.pnl_pct, 1, true)}</td>
                        <td>{fmtPct(p.weight, 1)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {d.effective_positions != null && (
            <section className="card stack">
              <h2 className="row" style={{ gap: 6 }}>Diversificación <Help term="effective_positions" /></h2>
              <p className="small" style={{ lineHeight: 1.55 }}>
                Tienes {d.positions.length} {d.positions.length === 1 ? "posición" : "posiciones"}, equivalentes a <strong>{fmtNum(d.effective_positions, 1)}</strong> de tamaño igual.
              </p>
              <div className="grid two">
                <Bars title="Por sector" data={d.by_sector} />
                <Bars title="Por país" data={d.by_country} />
              </div>
            </section>
          )}

          <section className="card stack">
            <h2>Historial de operaciones</h2>
            {delError && <div className="error-box small" role="alert">{delError}</div>}
            {trades.data && trades.data.length > 0 && (
              <div className="table-wrap">
                <table className="data">
                  <thead><tr><th>Fecha</th><th>Operación</th><th>Valor</th><th>Cantidad</th><th>Precio</th><th>Comisión</th><th>Motivo</th><th><span className="visually-hidden">Acciones</span></th></tr></thead>
                  <tbody>
                    {trades.data.map((t) => (
                      <tr key={t.id}>
                        <td>{fmtDate(t.trade_date)}</td>
                        <td>{t.side === "BUY" ? "Compra" : "Venta"}</td>
                        <td className="strong">{t.ticker}</td>
                        <td>{fmtNum(t.quantity, 2)}</td>
                        <td>{fmtMoney(t.price, t.currency)}</td>
                        <td>{fmtMoney(t.fee, t.currency)}</td>
                        <td className="small muted">{t.note ?? ""}</td>
                        <td><button className="btn small" onClick={() => del(t.id)} aria-label={`Borrar la operación de ${t.ticker} del ${fmtDate(t.trade_date)}`}>Borrar</button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p className="tiny muted">Apuntar el motivo de cada operación te permite revisar más adelante si tu razonamiento era bueno, con independencia del resultado.</p>
          </section>
        </>
      )}
    </div>
  );
}
