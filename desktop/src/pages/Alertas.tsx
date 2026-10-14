import { useState } from "react";
import { api, invalidate, useApi } from "../api";
import { ErrorBox, Loading } from "../components/ui";
import { fmtDateTime, fmtNum } from "../format";
import type { AlertsData } from "../types";
import { inputStyle } from "./Cartera";

export function Alertas() {
  const { data, error, reload } = useApi<AlertsData>("/api/alerts");
  const [f, setF] = useState({ ticker: "", metric: "price", op: "above", threshold: "" });
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const usesAverage = f.metric === "sma50" || f.metric === "sma200";
  const refresh = () => { invalidate("/api/alerts"); };

  const add = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setMsg(null);
    try {
      await api("/api/alerts", { method: "POST", body: JSON.stringify({ ticker: f.ticker, metric: f.metric, op: f.op, threshold: usesAverage ? null : Number(f.threshold.replace(",", ".")) }) });
      setF((o) => ({ ...o, ticker: "", threshold: "" }));
      refresh();
    } catch (err) {
      setMsg((err as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const act = async (fn: () => Promise<unknown>) => {
    setMsg(null);
    try { await fn(); refresh(); } catch (err) { setMsg((err as Error).message); }
  };
  const check = () => act(async () => {
    const r = await api<{ fired: string[] }>("/api/alerts/check", { method: "POST" });
    setMsg(r.fired.length ? `${r.fired.length} alerta(s) disparada(s).` : "Ninguna alerta disparada ahora mismo.");
  });
  const unseen = data?.events.filter((e) => !e.seen).length ?? 0;

  return (
    <div className="stack" style={{ gap: 20, maxWidth: 920 }}>
      <div>
        <h1>Alertas</h1>
        <p className="muted" style={{ marginTop: 6, lineHeight: 1.55 }}>
          Te avisan con una notificación de macOS cuando un valor cruza el umbral que fijas. La app las comprueba cada 5 minutos mientras está abierta. Salta al <strong>cruzar</strong> el umbral, no mientras se cumple. Las cotizaciones de Yahoo llevan retraso de unos 15 minutos.
        </p>
      </div>

      <section className="card stack">
        <h2>Nueva alerta</h2>
        <form className="stack" onSubmit={add}>
          <div className="row wrap" style={{ alignItems: "flex-end" }}>
            <label className="stack tight" style={{ flex: "1 1 140px" }}><span className="small strong">Ticker</span><input style={inputStyle} value={f.ticker} onChange={(e) => setF({ ...f, ticker: e.target.value })} required /></label>
            <label className="stack tight" style={{ flex: "1 1 200px" }}><span className="small strong">Condición</span>
              <select style={inputStyle} value={f.metric} onChange={(e) => setF({ ...f, metric: e.target.value })}>
                {Object.entries(data?.metrics ?? { price: "Precio" }).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select></label>
            <label className="stack tight" style={{ flex: "1 1 140px" }}><span className="small strong">Cuando esté</span>
              <select style={inputStyle} value={f.op} onChange={(e) => setF({ ...f, op: e.target.value })}><option value="above">por encima de</option><option value="below">por debajo de</option></select></label>
            {!usesAverage && <label className="stack tight" style={{ flex: "1 1 110px" }}><span className="small strong">Valor</span><input style={inputStyle} inputMode="decimal" value={f.threshold} onChange={(e) => setF({ ...f, threshold: e.target.value })} required /></label>}
            <button className="btn primary" type="submit" disabled={busy || !f.ticker}>{busy ? "Creando…" : "Crear alerta"}</button>
          </div>
        </form>
        {msg && <div className="error-box small" role="status">{msg}</div>}
      </section>

      {error && <ErrorBox error={error} onRetry={reload} />}
      {!data && !error && <Loading height={140} />}
      {data && (
        <>
          <section className="card stack">
            <div className="row between wrap">
              <h2>Mis alertas</h2>
              <button className="btn small" onClick={check}>Comprobar ahora</button>
            </div>
            {data.alerts.length === 0 ? <p className="muted small">Aún no tienes alertas.</p> : (
              <div className="table-wrap">
                <table className="data">
                  <thead><tr><th>Alerta</th><th>Último valor</th><th>Última comprobación</th><th>Estado</th><th><span className="visually-hidden">Acciones</span></th></tr></thead>
                  <tbody>
                    {data.alerts.map((a) => (
                      <tr key={a.id}>
                        <td className="strong">{a.text}</td>
                        <td>{a.last_value == null ? "n/d" : fmtNum(a.last_value, 2)}</td>
                        <td className="small muted">{a.last_checked_at ? fmtDateTime(a.last_checked_at) : "sin comprobar"}</td>
                        <td>{a.active ? "Activa" : "Pausada"}</td>
                        <td className="row" style={{ gap: 6 }}>
                          <button className="btn small" onClick={() => act(() => api(`/api/alerts/${a.id}/active?active=${!a.active}`, { method: "PUT" }))}>{a.active ? "Pausar" : "Activar"}</button>
                          <button className="btn small" onClick={() => act(() => api(`/api/alerts/${a.id}`, { method: "DELETE" }))} aria-label={`Borrar la alerta ${a.text}`}>Borrar</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="card stack">
            <div className="row between wrap">
              <h2>Avisos recientes{unseen > 0 ? ` (${unseen} sin ver)` : ""}</h2>
              {unseen > 0 && <button className="btn small" onClick={() => act(() => api("/api/alerts/seen", { method: "POST" }))}>Marcar como vistos</button>}
            </div>
            {data.events.length === 0 ? <p className="muted small">Todavía no ha saltado ninguna alerta.</p> : (
              <ul style={{ paddingLeft: 0, listStyle: "none", display: "grid", gap: 8 }}>
                {data.events.map((e) => (
                  <li key={e.id} className="small" style={{ fontWeight: e.seen ? 400 : 700 }}>
                    <span className="muted">{fmtDateTime(e.triggered_at)}</span> · {e.message}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  );
}
