import { useState } from "react";
import { useApi } from "../api";
import { PriceChart } from "../components/charts";
import { IconAlert, IconArrowUp, IconBack, IconBook, IconCheck, IconX } from "../components/Icons";
import type { Page } from "../components/Shell";
import { ErrorBox, Help, LabelIcon, Loading, Modal, RangeBar, ScoreBar, Stamp, scoreTone } from "../components/ui";
import { fmtBig, fmtDate, fmtDateTime, fmtMoney, fmtNum, fmtPct } from "../format";
import type { ComponentScore, History, InputScore, Quote, RecDetail } from "../types";

const RANGES = [
  ["1M", "1M"],
  ["6M", "6M"],
  ["1A", "1A"],
  ["5A", "5A"],
  ["MAX", "Máx."],
] as const;

// Métricas en % (fracción) frente a ratios; el resto se muestran como número.
const PCT_KEYS = new Set([
  "fcf_yield", "operating_margin", "roe", "revenue_growth", "earnings_growth", "fcf_margin",
  "ret_12m", "ret_6m", "dist_sma200", "vol_1y", "mdd_1y", "dividend_yield", "payout_ratio",
  "expense_ratio",
]);

function fmtInput(i: InputScore, v: number | null, currency: string | null): string {
  if (i.key === "total_assets") return fmtBig(v, currency);
  return PCT_KEYS.has(i.key) ? fmtPct(v, i.key === "expense_ratio" ? 2 : 1) : fmtNum(v, 2);
}

function ComponentRow({ c, currency }: { c: ComponentScore; currency: string | null }) {
  const [open, setOpen] = useState(false);
  const counts = c.weight > 0;
  return (
    <div className="stack tight" style={{ opacity: counts ? 1 : 0.6 }}>
      <div style={{ display: "grid", gridTemplateColumns: "minmax(150px, 230px) minmax(0, 1fr) 46px 92px", alignItems: "center", gap: 14 }}>
        <div className="row" style={{ gap: 8, fontWeight: 600 }}>
          {c.label}
          <Help title={c.label} text={c.description} />
        </div>
        <ScoreBar score={c.score} />
        <div className="strong" style={{ textAlign: "right", fontSize: 16 }}>{c.score == null ? "—" : Math.round(c.score)}</div>
        <button className="btn small" onClick={() => setOpen(!open)} aria-expanded={open}>
          {counts ? `peso ${Math.round(c.effective_weight * 100)} %` : "no cuenta"}
        </button>
      </div>
      {open && (
        <div className="table-wrap">
          <table className="data" style={{ minWidth: 560 }}>
            <thead>
              <tr>
                <th>Dato</th>
                <th>Valor</th>
                <th>Mediana comparables</th>
                <th>Mejor que el…</th>
              </tr>
            </thead>
            <tbody>
              {c.inputs.map((i) => (
                <tr key={i.key} style={{ cursor: "default" }}>
                  <td>
                    <span className="row" style={{ gap: 6 }}>{i.label} <Help term={i.key} /></span>
                  </td>
                  <td>{fmtInput(i, i.value, currency)}</td>
                  <td>{fmtInput(i, i.peer_median, currency)}</td>
                  <td>{i.percentile == null ? "sin dato" : `${Math.round(i.percentile * 100)} %`}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="tiny muted" style={{ padding: "8px 12px" }}>
            Comparables: {c.basis_label}. Puntuación = media de los percentiles × 100.
          </div>
        </div>
      )}
    </div>
  );
}

function HowToBuy({ d, onClose }: { d: RecDetail; onClose: () => void }) {
  const p = d.profile;
  const isEtf = d.kind === "etf";
  const share = isEtf ? p.allocation.etf : p.allocation.stocks;
  const perPosition = isEtf ? (p.amount_eur * share) / 100 : p.positions ? (p.amount_eur * share) / 100 / p.positions : 0;
  const shares = d.price && d.currency === "EUR" && perPosition ? Math.floor(perPosition / d.price) : null;
  const m = d.market;
  const limit = d.entry?.high != null && d.price != null ? Math.min(d.entry.high, d.price) : d.price;
  return (
    <Modal title={`Cómo comprar ${d.name}`} onClose={onClose}>
      <ol className="steps">
        <li>
          <strong>Dónde cotiza:</strong> {m.exchange ?? "bolsa desconocida"}
          {m.country ? ` (${m.country})` : ""}, en {d.currency ?? "su moneda"}, con el ticker <strong>{d.ticker}</strong>.
          {m.opens && ` Horario de la sesión: ${m.opens}–${m.closes} (hora local de ${m.tz}).`}
          {d.ticker.endsWith(".MC")
            ? " Cualquier bróker que opere en la Bolsa de Madrid te sirve."
            : " Necesitas un bróker con acceso a esa bolsa; casi todos los brókeres online lo tienen."}
        </li>
        <li>
          <strong>Tipo de orden: limitada.</strong> Fija el precio máximo que aceptas pagar
          {limit != null ? ` (por ejemplo, ${fmtMoney(limit, d.currency)}${d.entry?.high != null ? ", sin pasar del máximo del rango de entrada" : ", cerca del último precio"})` : ""}. Una orden «a
          mercado» compra al precio que haya en ese momento, y fuera de horario o en valores poco líquidos puede salir cara.
        </li>
        <li>
          <strong>Con cuánto empezar:</strong>{" "}
          {perPosition > 0 ? (
            <>
              con tu perfil {p.label} (unos {fmtMoney(p.amount_eur, "EUR")} y un {share} % en {isEtf ? "ETFs" : "acciones"}
              {isEtf ? "" : ` repartido entre unas ${p.positions} empresas`}), una referencia sería{" "}
              <strong>{fmtMoney(perPosition, "EUR")}</strong>
              {shares != null && shares > 0 ? ` (unas ${shares} participaciones a ${fmtMoney(d.price, d.currency)})` : ""}.
              {isEtf && " En un ETF indexado encaja repartirlo en aportaciones mensuales."}
            </>
          ) : (
            <>con tu perfil, el reparto sugerido no incluye acciones sueltas: la base es un ETF indexado.</>
          )}
        </li>
        <li>
          <strong>Impuestos:</strong> las ganancias al vender y los dividendos tributan en la base del ahorro del IRPF.
          {d.ticker.endsWith(".MC") ? " Los dividendos españoles llevan una retención del 19 %." : " Los dividendos extranjeros pueden sufrir doble retención (en origen y en España)."}
        </li>
      </ol>
      <div className="card soft small muted">
        Pasos orientativos. La guía completa (elegir bróker, comisiones, Modelo 720/721) llegará a la sección «Cómo
        invertir».
      </div>
    </Modal>
  );
}

export function Detalle({ ticker, go }: { ticker: string; go: (p: Page) => void }) {
  const { data: d, error, reload } = useApi<RecDetail>(`/api/recommendations/${encodeURIComponent(ticker)}`);
  const quote = useApi<Quote>(`/api/quote/${encodeURIComponent(ticker)}`);
  const [range, setRange] = useState("1A");
  const hist = useApi<History>(`/api/history/${encodeURIComponent(ticker)}?range=${range}`);
  const [howTo, setHowTo] = useState(false);

  const back = (
    <button className="btn small" style={{ alignSelf: "flex-start" }} onClick={() => go({ name: "recs" })}>
      <IconBack /> Mis recomendaciones
    </button>
  );
  if (error) return <div className="stack">{back}<ErrorBox error={error} onRetry={reload} /></div>;
  if (!d) return <div className="stack">{back}<Loading height={300} /><Loading height={200} /></div>;

  const q = quote.data;
  const price = q?.price ?? d.price;
  const tone = d.label;

  return (
    <div className="stack" style={{ gap: 20 }}>
      {back}
      {d.profile_is_default && (
        <div className="card soft small">Aún no has hecho el test de perfil: la señal usa un perfil moderado de referencia. <a onClick={() => go({ name: "perfil" })}>Hacer el test</a></div>
      )}

      <section className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 20 }}>
        <div className="card stack" style={{ gridColumn: "span 2", minWidth: 0 }}>
          <div className="row between wrap" style={{ alignItems: "flex-start" }}>
            <div>
              <h1>{d.name}</h1>
              <div className="muted small" style={{ marginTop: 4 }}>
                {d.ticker} · {d.market.exchange ?? "—"} · {d.kind === "etf" ? `ETF · ${d.etf_role_es}` : "Acción"} · {d.currency}
                {d.sector_es ? ` · ${d.sector_es}` : ""}
                {d.spain_index ? ` · ${d.spain_index}` : ""}
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: 28, fontWeight: 800 }}>{fmtMoney(price, q?.currency ?? d.currency)}</div>
              {q?.change_pct != null && (
                <div className={`strong small ${q.change_pct >= 0 ? "up" : "down"}`}>
                  {q.change_pct >= 0 ? "▲" : "▼"} {fmtPct(q.change_pct, 2, true)} hoy
                </div>
              )}
            </div>
          </div>
          {hist.data ? <PriceChart points={hist.data.points} currency={d.currency} /> : hist.error ? <div className="empty">{hist.error.message}</div> : <Loading height={220} />}
          <div className="row wrap between" style={{ gap: 8 }}>
            <div className="row" style={{ gap: 6 }}>
              {RANGES.map(([k, t]) => (
                <button key={k} className="chip small" aria-pressed={range === k} onClick={() => setRange(k)}>{t}</button>
              ))}
            </div>
            {q && <Stamp source={q.source} at={q.as_of} delay={q.delay_minutes} stale={q.stale} prefix="Cotización:" />}
          </div>
        </div>

        <div className={`card stack tone-${tone}`} style={{ borderColor: "transparent", color: "var(--text)" }}>
          <div className="row between">
            <span className={`small strong text-${tone}`} style={{ textTransform: "uppercase", letterSpacing: "0.06em" }}>Señal del modelo</span>
            <Help term="model_label" />
          </div>
          <div className={`row text-${tone}`} style={{ gap: 10, fontSize: 32, fontWeight: 800 }}>
            <LabelIcon label={tone} size={32} />
            {d.label_es}
          </div>
          <p style={{ lineHeight: 1.45 }}>
            Puntuación <strong>{d.score == null ? "sin dato" : `${Math.round(d.score)}/100`}</strong>
            {d.score != null && d.kind === "stock" && `: sus números son mejores que los del ${Math.round(d.score)} % de sus comparables, de media.`}
            {d.score != null && d.kind === "etf" && " frente a los demás ETFs de referencia."}
          </p>
          <p style={{ lineHeight: 1.45 }} className="small"><strong>{d.fit}</strong></p>
          <div className="stack tight">
            {d.checks.map((c) => (
              <div key={c.rule} className="check">
                <span className={c.passed ? "text-buy" : "text-avoid"}>{c.passed ? <IconCheck /> : <IconX />}</span>
                <span>
                  {c.rule}
                  <span className="muted small"> · {c.detail}</span>
                </span>
              </div>
            ))}
          </div>
          <div className="stack tight" style={{ marginTop: "auto" }}>
            <button className="btn primary" onClick={() => setHowTo(true)}>
              <IconBook /> Cómo comprar esto
            </button>
          </div>
        </div>
      </section>

      <section className="grid two">
        <div className="card stack">
          <h2 className="row text-buy" style={{ gap: 8 }}><IconArrowUp /> {d.pros.length === 3 ? "3 razones a favor" : "Razones a favor"}</h2>
          {d.pros.length === 0 && <p className="muted">Ninguna métrica destaca claramente para bien frente a sus comparables.</p>}
          {d.pros.map((p, i) => (
            <div key={i} className="numbered">
              <span className="tone-buy">{i + 1}</span>
              <div style={{ lineHeight: 1.45 }}>
                {p.text} {p.data && <span className="muted small">{p.data}</span>}
              </div>
            </div>
          ))}
        </div>
        <div className="card stack">
          <h2 className="row text-avoid" style={{ gap: 8 }}><IconAlert /> {d.cons.length === 3 ? "3 riesgos" : "Riesgos"}</h2>
          {d.cons.map((p, i) => (
            <div key={i} className="numbered">
              <span className="tone-avoid">{i + 1}</span>
              <div style={{ lineHeight: 1.45 }}>
                {p.text} {p.data && <span className="muted small">{p.data}</span>}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="grid two">
        <div className="card stack">
          <h2 className="row" style={{ gap: 8 }}>
            Rango de entrada razonable <Help term="entry_range" />
          </h2>
          {d.entry?.low != null && d.entry.high != null ? (
            <>
              <div style={{ fontSize: 24, fontWeight: 800 }}>
                {fmtMoney(d.entry.low, d.currency)} – {fmtMoney(d.entry.high, d.currency)}
              </div>
              <RangeBar low={d.entry.low} high={d.entry.high} price={d.price} currency={d.currency} showLabel />
            </>
          ) : (
            <div style={{ fontSize: 20, fontWeight: 800 }}>{d.kind === "etf" ? "Aportaciones periódicas" : "Sin rango fiable"}</div>
          )}
          <p className="muted small" style={{ lineHeight: 1.5 }}>{d.entry?.note ?? d.entry_note}</p>
          {d.entry && d.entry.estimates.length > 0 && (
            <div className="table-wrap">
              <table className="data" style={{ minWidth: 0 }}>
                <thead>
                  <tr><th>Método</th><th>Suyo</th><th>Sector</th><th>Precio estimado</th></tr>
                </thead>
                <tbody>
                  {d.entry.estimates.map((e) => (
                    <tr key={e.metric} style={{ cursor: "default" }}>
                      <td>{e.method}</td>
                      <td>{e.metric === "fcf_yield" ? fmtPct(e.value) : fmtNum(e.value, 2)}</td>
                      <td>{e.metric === "fcf_yield" ? fmtPct(e.peer_median) : fmtNum(e.peer_median, 2)}</td>
                      <td>{fmtMoney(e.estimate, d.currency)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="tiny muted" style={{ padding: "8px 12px" }}>Comparables: {d.entry.peer_group}.</div>
            </div>
          )}
        </div>
        <div className="card stack">
          <h2 className="row" style={{ gap: 8 }}>
            Nivel de riesgo <Help term="risk_level" />
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 6 }}>
            {["Bajo", "Medio", "Alto"].map((t, i) => (
              <div
                key={t}
                className={d.risk_level === i ? `tone-${["buy", "watch", "avoid"][i]}` : "tone-neutral"}
                style={{ height: 40, borderRadius: 10, display: "grid", placeItems: "center", fontWeight: d.risk_level === i ? 800 : 500 }}
                aria-current={d.risk_level === i}
              >
                {t}
              </div>
            ))}
          </div>
          <p className="muted small" style={{ lineHeight: 1.5 }}>{d.risk_detail}</p>
          {d.etf && (
            <p className="small" style={{ lineHeight: 1.5 }}>
              Replica el índice <strong>{d.etf.index}</strong> · zona {d.etf.zone} ·{" "}
              {d.etf.accumulating ? "acumula los dividendos" : "reparte dividendos"}. Comisión anual (TER):{" "}
              <strong>{d.row?.expense_ratio != null ? fmtPct(Number(d.row.expense_ratio), 2) : "n/d en la fuente (consúltala en su KID)"}</strong>
            </p>
          )}
          {d.row?.market_cap != null && d.kind === "stock" && (
            <p className="small muted">Capitalización: {fmtBig(Number(d.row.market_cap), String(d.row.currency ?? d.currency))}</p>
          )}
        </div>
      </section>

      <section className="card stack" style={{ gap: 16 }}>
        <div className="row between wrap">
          <h2>De dónde sale {d.score == null ? "la puntuación" : `el ${Math.round(d.score)}`}</h2>
          <span className="muted small">Pulsa el peso de cada componente para ver sus datos</span>
        </div>
        {d.components.map((c) => (
          <ComponentRow key={c.key} c={c} currency={d.currency} />
        ))}
        {d.notes.map((n) => (
          <p key={n} className="muted small">{n}</p>
        ))}
        <div className={`tiny muted`} style={{ lineHeight: 1.6 }}>
          Fuente: {d.source}. Fundamentales descargados el {fmtDateTime(d.as_of.fundamentals_as_of)}
          {d.as_of.last_report ? ` (último trimestre publicado: ${fmtDate(d.as_of.last_report)})` : ""}. Precios: {fmtDateTime(d.as_of.history_as_of)}.
          Tono de la puntuación: <span className={`text-${scoreTone(d.score)}`}>{scoreTone(d.score) === "buy" ? "alta" : scoreTone(d.score) === "watch" ? "media" : "baja"}</span>.
        </div>
      </section>

      {howTo && <HowToBuy d={d} onClose={() => setHowTo(false)} />}
    </div>
  );
}
