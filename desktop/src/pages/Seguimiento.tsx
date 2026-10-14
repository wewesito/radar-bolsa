import { useState } from "react";
import { api, invalidate, useApi } from "../api";
import { ErrorBox, LabelPill, Loading, Stamp } from "../components/ui";
import { fmtMoney, fmtNum, fmtPct } from "../format";
import type { WatchItem } from "../types";

export function Seguimiento() {
  const { data, error, reload } = useApi<WatchItem[]>("/api/watchlist");
  const [msg, setMsg] = useState<string | null>(null);
  const remove = async (t: string) => {
    setMsg(null);
    try {
      await api(`/api/watchlist/${encodeURIComponent(t)}`, { method: "DELETE" });
      invalidate("/api/watchlist");
    } catch (e) {
      setMsg((e as Error).message);
    }
  };
  return (
    <div className="stack" style={{ gap: 20 }}>
      <div>
        <h1>Seguimiento</h1>
        <p className="muted" style={{ marginTop: 6, lineHeight: 1.55 }}>
          Tus valores favoritos. Para añadir uno, búscalo arriba, abre su ficha y pulsa «Seguir».
        </p>
      </div>
      {error && <ErrorBox error={error} onRetry={reload} />}
      {msg && <div className="error-box small" role="alert">{msg}</div>}
      {!data && !error && <Loading height={120} count={2} />}
      {data && data.length === 0 && <div className="empty">Todavía no sigues ningún valor.</div>}
      {data && data.length > 0 && (
        <div className="card">
          <div className="table-wrap">
            <table className="data">
              <thead><tr><th>Valor</th><th>Señal del modelo</th><th>Puntos</th><th>Precio</th><th>Hoy</th><th>Dato</th><th><span className="visually-hidden">Acciones</span></th></tr></thead>
              <tbody>
                {data.map((w) => {
                  const q = w.quote;
                  return (
                    <tr key={w.ticker}>
                      <td><a href={`#/detalle/${encodeURIComponent(w.ticker)}`}><span className="strong">{w.name}</span></a> <span className="tiny muted">{w.ticker}</span></td>
                      <td>{w.label ? <LabelPill label={w.label} /> : <span className="muted small">n/d</span>}</td>
                      <td>{w.score == null ? "n/d" : fmtNum(w.score, 0)}</td>
                      <td>{q ? fmtMoney(q.price, q.currency) : "n/d"}</td>
                      <td className={(q?.change_pct ?? 0) >= 0 ? "up" : "down"}>{q?.change_pct == null ? "n/d" : `${q.change_pct >= 0 ? "▲" : "▼"} ${fmtPct(q.change_pct, 2, true)}`}</td>
                      <td className="tiny muted">{q ? <Stamp source={q.source} at={q.as_of} delay={q.delay_minutes} stale={q.stale} /> : "sin cotización"}</td>
                      <td><button className="btn small" onClick={() => remove(w.ticker)} aria-label={`Dejar de seguir ${w.name}`}>Quitar</button></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
