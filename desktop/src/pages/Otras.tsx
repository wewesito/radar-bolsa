import { useMemo, useState } from "react";
import { api, useApi } from "../api";
import { CompoundCalculator, TaxCalculator } from "../components/Calculators";
import { Sparkline } from "../components/charts";
import { Markdown } from "../components/Markdown";
import type { Page } from "../components/Shell";
import { ErrorBox, LabelPill, Loading, Stamp } from "../components/ui";
import { fmtDateTime, fmtNum, fmtPct } from "../format";
import type { GlossaryEntry, GuidesData, MarketTile, RecList, UniverseStatus } from "../types";

function greeting(): string {
  const h = Number(new Intl.DateTimeFormat("es-ES", { hour: "numeric", hour12: false, timeZone: "Europe/Madrid" }).format(new Date()));
  return h < 14 ? "Buenos días" : h < 21 ? "Buenas tardes" : "Buenas noches";
}

export function Inicio({ go, status }: { go: (p: Page) => void; status?: UniverseStatus }) {
  const markets = useApi<MarketTile[]>("/api/markets");
  const recs = useApi<RecList>("/api/recommendations");
  const today = new Intl.DateTimeFormat("es-ES", { weekday: "long", day: "numeric", month: "long", year: "numeric", timeZone: "Europe/Madrid" }).format(new Date());
  const top = (recs.data?.items ?? []).filter((r) => r.label === "buy").slice(0, 3);

  return (
    <div className="stack" style={{ gap: 22 }}>
      <div>
        <h1>{greeting()}</h1>
        <p className="muted" style={{ marginTop: 6, textTransform: "none" }}>
          {today.charAt(0).toUpperCase() + today.slice(1)} · horas en hora de Madrid
        </p>
      </div>

      <section aria-label="Mercados" className="grid tiles">
        {markets.error && <ErrorBox error={markets.error} onRetry={markets.reload} />}
        {!markets.data && !markets.error && <Loading height={130} count={4} />}
        {markets.data?.map((m) => (
          <div key={m.ticker} className="card stack tight">
            <div className="row between small strong muted">
              <span>{m.label}</span>
              <span className="tiny">{m.as_of ? fmtDateTime(m.as_of).slice(11) : ""}</span>
            </div>
            {m.error ? (
              <span className="muted small">{m.error}</span>
            ) : (
              <>
                <div style={{ fontSize: 23, fontWeight: 800 }}>{fmtNum(m.price ?? null, m.ticker === "EURUSD=X" ? 4 : 2)}</div>
                <div className={`small strong ${(m.change_pct ?? 0) >= 0 ? "up" : "down"}`}>
                  {(m.change_pct ?? 0) >= 0 ? "▲" : "▼"} {fmtPct(m.change_pct ?? null, 2, true)}
                </div>
                <Sparkline values={m.spark ?? []} tone={(m.spark?.at(-1) ?? 0) >= (m.spark?.[0] ?? 0) ? "up" : "down"} />
                <span className="tiny muted">
                  Línea: último mes · {m.source}
                  {m.delay_minutes ? ` · retraso ~${m.delay_minutes} min` : ""}
                  {m.stale ? " · copia antigua" : ""}
                </span>
              </>
            )}
          </div>
        ))}
      </section>

      <section className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 20 }}>
        <div className="card stack" style={{ gridColumn: "span 2" }}>
          <div className="row between">
            <h2>Tus mejores oportunidades hoy</h2>
            <a onClick={() => go({ name: "recs" })}>Ver todas →</a>
          </div>
          {recs.error?.code === "no_profile" && <p className="muted">Haz el test de perfil para ver tus recomendaciones.</p>}
          {!recs.data && !recs.error && <Loading height={64} count={3} />}
          {recs.data && top.length === 0 && <p className="muted">Hoy ningún valor cumple todas las condiciones con tu perfil.</p>}
          {top.map((r) => (
            <button key={r.ticker} className="card soft card-link row" style={{ padding: "12px 14px" }} onClick={() => go({ name: "detalle", ticker: r.ticker })}>
              <span style={{ flex: 1, minWidth: 0 }}>
                <span className="strong" style={{ display: "block" }}>{r.name}</span>
                <span className="muted small">{r.ticker} · {r.summary}</span>
              </span>
              <span style={{ fontSize: 20, fontWeight: 800 }}>{r.score == null ? "—" : Math.round(r.score)}</span>
              <LabelPill label={r.label} />
            </button>
          ))}
        </div>
        <div className="stack" style={{ gap: 20 }}>
          <button className="card card-link stack tight" onClick={() => go({ name: "espana" })}>
            <h2>España</h2>
            <p className="muted small">Rankings del IBEX 35 y el Mercado Continuo por rentabilidad, negocio, dividendo y valoración.</p>
            <span className="small strong" style={{ color: "var(--accent-text)" }}>Abrir →</span>
          </button>
          <div className="card stack tight">
            <h2>Datos</h2>
            {status?.built_at ? (
              <>
                <Stamp source={status.source} at={status.built_at} stale={status.stale} />
                <p className="muted small">
                  {status.rows} valores analizados. {status.stale ? "Tienen más de una semana: conviene actualizarlos." : "Los fundamentales cambian cada trimestre; con actualizar una vez por semana basta."}
                </p>
              </>
            ) : (
              <p className="muted small">Sin datos todavía.</p>
            )}
          </div>
        </div>
      </section>

      <section className="card row wrap" style={{ background: "var(--accent-soft)", borderColor: "transparent", gap: 16 }}>
        <div style={{ flex: "1 1 360px" }}>
          <div className="small strong" style={{ color: "var(--accent-text)", textTransform: "uppercase", letterSpacing: "0.06em" }}>Aprende en 2 minutos</div>
          <div className="strong" style={{ fontSize: 18, marginTop: 4 }}>¿Qué significa cada número de la app?</div>
          <div className="muted small" style={{ marginTop: 4 }}>PER, ROE, payout, volatilidad… explicados con ejemplos y sus limitaciones.</div>
        </div>
        <button className="btn primary" onClick={() => go({ name: "aprender" })}>Abrir el glosario</button>
      </section>
    </div>
  );
}

type Mode = "glosario" | "conceptos" | "calculadoras";
const MODES: [Mode, string][] = [["glosario", "Glosario de métricas"], ["conceptos", "Conceptos básicos"], ["calculadoras", "Calculadoras"]];

function Glosario() {
  const { data, error, reload } = useApi<{ entries: GlossaryEntry[] }>("/api/glossary");
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("Todas");
  const fold = (s: string) => s.toLowerCase().normalize("NFD").replace(/\p{Diacritic}/gu, "");
  const cats = useMemo(() => ["Todas", ...new Set((data?.entries ?? []).map((e) => e.category))], [data]);
  const items = (data?.entries ?? []).filter(
    (e) => (cat === "Todas" || e.category === cat) && (!q || fold(e.term + " " + e.what).includes(fold(q))),
  );
  return (
    <>
      <div className="search" style={{ flex: "0 1 420px" }}>
        <label>
          <span className="visually-hidden">Buscar en el glosario</span>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Busca un término: PER, payout, volatilidad…" />
        </label>
      </div>
      <div className="row wrap" style={{ gap: 8 }}>
        {cats.map((c) => (
          <button key={c} className="chip small" aria-pressed={cat === c} onClick={() => setCat(c)}>{c}</button>
        ))}
      </div>
      {error && <ErrorBox error={error} onRetry={reload} />}
      {!data && !error && <Loading count={3} height={120} />}
      <div className="grid two">
        {items.map((e) => (
          <article key={e.key} className="card stack tight" style={{ gap: 8 }}>
            <span className="badge" style={{ alignSelf: "flex-start" }}>{e.category}</span>
            <h2>{e.term}</h2>
            <p style={{ lineHeight: 1.5 }}>{e.what}</p>
            <p className="small" style={{ lineHeight: 1.5 }}><strong>Cálculo:</strong> {e.formula}</p>
            <p className="small" style={{ lineHeight: 1.5 }}><strong>Cómo leerlo:</strong> {e.reading}</p>
            <p className="small muted" style={{ lineHeight: 1.5 }}><strong>Limitaciones:</strong> {e.limits}</p>
          </article>
        ))}
      </div>
    </>
  );
}

function Conceptos() {
  const { data, error, reload } = useApi<GuidesData>("/api/guides");
  return (
    <>
      {error && <ErrorBox error={error} onRetry={reload} />}
      {!data && !error && <Loading count={3} height={120} />}
      <div className="stack" style={{ gap: 14, maxWidth: 820 }}>
        {data?.concepts.map((c) => (
          <details key={c.title} className="card">
            <summary className="strong" style={{ cursor: "pointer", fontSize: 17 }}>{c.title}</summary>
            <div style={{ marginTop: 12 }}><Markdown text={c.body} /></div>
          </details>
        ))}
      </div>
    </>
  );
}

export function Aprender() {
  const [mode, setMode] = useState<Mode>("glosario");
  return (
    <div className="stack" style={{ gap: 20 }}>
      <div className="page-head">
        <div>
          <h1>Aprender</h1>
          <p className="muted">Glosario de todas las métricas, conceptos básicos de inversión y calculadoras. Contenido educativo, no asesoramiento.</p>
        </div>
      </div>
      <div className="row wrap" style={{ gap: 8 }} role="tablist" aria-label="Secciones">
        {MODES.map(([k, label]) => (
          <button key={k} role="tab" aria-selected={mode === k} className="chip" aria-pressed={mode === k} onClick={() => setMode(k)}>{label}</button>
        ))}
      </div>
      {mode === "glosario" && <Glosario />}
      {mode === "conceptos" && <Conceptos />}
      {mode === "calculadoras" && (
        <div className="stack" style={{ maxWidth: 820 }}>
          <CompoundCalculator />
          <TaxCalculator />
        </div>
      )}
    </div>
  );
}

export function Ajustes({ status, onRebuild }: { status?: UniverseStatus; onRebuild: () => void }) {
  const secrets = useApi<Record<string, boolean>>("/api/settings/secrets");
  const [key, setKey] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const save = async (value: string) => {
    setMsg(null);
    try {
      await api("/api/settings/secrets", { method: "PUT", body: JSON.stringify({ name: "finnhub", value }) });
      setKey("");
      secrets.reload();
      setMsg(value ? "Clave guardada en el Llavero de macOS." : "Clave borrada.");
    } catch (e) {
      setMsg((e as Error).message);
    }
  };
  const b = status?.build;
  return (
    <div className="stack" style={{ gap: 20, maxWidth: 760 }}>
      <h1>Ajustes</h1>
      <section className="card stack">
        <h2>Datos de mercado</h2>
        {status?.built_at && <Stamp source={status.source} at={status.built_at} stale={status.stale} prefix="Última actualización:" />}
        <p className="muted small" style={{ lineHeight: 1.5 }}>
          La app descarga fundamentales y precios de unos {status?.rows || 225} valores (IBEX 35, Mercado Continuo, Euro Stoxx 50, grandes de EE. UU. y ETFs). Tarda alrededor de un minuto. Las cotizaciones del día se refrescan solas cada minuto.
        </p>
        {b?.running ? (
          <div className="stack tight" aria-live="polite">
            <div className="progress"><div style={{ width: `${b.total ? (b.done / b.total) * 100 : 3}%` }} /></div>
            <span className="small muted">Descargando {b.done} de {b.total || "…"}</span>
          </div>
        ) : (
          <button className="btn" style={{ alignSelf: "flex-start" }} onClick={onRebuild}>Actualizar datos ahora</button>
        )}
        {b?.error && <div className="error-box small">{b.error}</div>}
        {status && status.failed.length > 0 && <p className="tiny muted">Sin datos en la última descarga: {status.failed.join(", ")}.</p>}
      </section>
      <section className="card stack">
        <h2>API keys</h2>
        <p className="muted small" style={{ lineHeight: 1.5 }}>
          Se guardan en el Llavero de macOS, nunca en el código ni en la base de datos. Finnhub (opcional, plan gratuito) añade noticias de empresas de EE. UU.
        </p>
        <div className="row wrap">
          <span className={`pill ${secrets.data?.finnhub ? "tone-buy" : "tone-neutral"}`}>Finnhub: {secrets.data?.finnhub ? "configurada" : "sin configurar"}</span>
        </div>
        <form className="row wrap" onSubmit={(e) => { e.preventDefault(); save(key); }}>
          <label className="stack tight" style={{ flex: "1 1 300px" }}>
            <span className="small strong">Clave de Finnhub</span>
            <input type="password" autoComplete="off" value={key} onChange={(e) => setKey(e.target.value)} style={{ height: 42, borderRadius: 10, border: "1px solid var(--border)", background: "var(--surface2)", color: "var(--text)", padding: "0 12px", font: "inherit" }} />
          </label>
          <button className="btn primary" type="submit" disabled={!key.trim()} style={{ alignSelf: "flex-end" }}>Guardar</button>
          {secrets.data?.finnhub && <button className="btn" type="button" onClick={() => save("")} style={{ alignSelf: "flex-end" }}>Borrar</button>}
        </form>
        {msg && <p className="small">{msg}</p>}
      </section>
      <section className="card stack tight">
        <h2>Acerca de</h2>
        <p className="muted small" style={{ lineHeight: 1.5 }}>
          Radar Bolsa 0.2 · Fuente de datos: Yahoo Finance (no oficial, con retraso de unos 15 minutos en Europa). Tus datos (perfil, ajustes y caché) se guardan solo en este ordenador.
          No ejecuta operaciones ni se conecta a ningún bróker.
        </p>
      </section>
    </div>
  );
}

export function fmtUpdated(iso: string | null | undefined) {
  return fmtDateTime(iso);
}
