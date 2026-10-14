import { useMemo, useState, type ReactElement } from "react";
import { useApi } from "../api";
import type { Page } from "../components/Shell";
import { IconBan, IconCheckCircle, IconEye, IconShield } from "../components/Icons";
import { ErrorBox, Help, LabelPill, Loading, RangeBar, RiskPill, ScoreBar, Stamp } from "../components/ui";
import { fmtDate, fmtMoney } from "../format";
import type { Label, RecList, RecSummary } from "../types";

const PAGE = 24;

export function RecCard({ r, go }: { r: RecSummary; go: (p: Page) => void }) {
  return (
    <button className="card card-link stack" style={{ gap: 14 }} onClick={() => go({ name: "detalle", ticker: r.ticker })}>
      <div className="row between" style={{ alignItems: "flex-start" }}>
        <div style={{ minWidth: 0 }}>
          <div className="row wrap" style={{ gap: 8 }}>
            <span className="strong" style={{ fontSize: 17 }}>{r.name}</span>
            <span className="badge">{r.kind === "etf" ? "ETF" : "Acción"}</span>
          </div>
          <div className="muted small" style={{ marginTop: 3 }}>
            {r.ticker} · {r.market.exchange ?? "—"} · {r.currency ?? ""}
          </div>
        </div>
        <LabelPill label={r.label} />
      </div>
      <div className="row" style={{ gap: 14 }}>
        <div className="score-big">
          {r.score == null ? "—" : Math.round(r.score)}
          <span>/100</span>
        </div>
        <div className="stack tight" style={{ flex: 1 }}>
          <ScoreBar score={r.score} tone={r.label} />
          <div className="row small muted" style={{ gap: 6 }}>
            <IconShield /> Riesgo <RiskPill level={r.risk_level} />
          </div>
        </div>
      </div>
      <p style={{ lineHeight: 1.45, fontSize: 14 }}>{r.summary}</p>
      <div className="card soft stack tight" style={{ padding: "12px 14px", borderRadius: 12 }}>
        <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 18px" }}>
          <span className="muted tiny">Precio</span>
          <span className="muted tiny" style={{ textAlign: "right" }}>
            {r.kind === "etf" ? "Cómo entrar" : "Rango de entrada"}
          </span>
          <strong className="small">{fmtMoney(r.price, r.currency)}</strong>
          <strong className="small" style={{ textAlign: "right" }}>
            {r.entry ? `${fmtMoney(r.entry.low, r.currency)} – ${fmtMoney(r.entry.high, r.currency)}` : r.kind === "etf" ? "Aportaciones periódicas" : "Sin rango fiable"}
          </strong>
        </div>
        {r.entry && <RangeBar low={r.entry.low} high={r.entry.high} price={r.price} currency={r.currency} />}
      </div>
      <div className="row between tiny muted" style={{ marginTop: "auto" }}>
        <span>Yahoo Finance · {fmtDate(r.as_of.history_as_of)}</span>
        <span className="strong small" style={{ color: "var(--accent-text)", whiteSpace: "nowrap" }}>Ver detalle →</span>
      </div>
    </button>
  );
}

const LABEL_TILES: { key: Label; text: string; icon: ReactElement; sub: string }[] = [
  { key: "buy", text: "Comprar", icon: <IconCheckCircle size={18} />, sub: "cumplen todas las condiciones" },
  { key: "watch", text: "Vigilar", icon: <IconEye size={18} />, sub: "buenas, pero caras o con dudas" },
  { key: "avoid", text: "Evitar", icon: <IconBan size={18} />, sub: "métricas débiles o riesgo alto" },
];

export function Recomendaciones({ go }: { go: (p: Page) => void }) {
  const { data, error, reload } = useApi<RecList>("/api/recommendations");
  const [kind, setKind] = useState<"all" | "stock" | "etf">("all");
  const [label, setLabel] = useState<"all" | Label>("buy");
  const [region, setRegion] = useState<"all" | "es">("all");
  const [limit, setLimit] = useState(PAGE);

  const items = useMemo(
    () =>
      (data?.items ?? []).filter(
        (r) =>
          (kind === "all" || r.kind === kind) &&
          (label === "all" || r.label === label) &&
          (region === "all" || r.spain_index),
      ),
    [data, kind, label, region],
  );

  const chip = <T extends string>(value: T, current: T, set: (v: T) => void, text: string) => (
    <button key={value} className="chip" aria-pressed={value === current} onClick={() => { set(value); setLimit(PAGE); }}>
      {text}
    </button>
  );

  return (
    <div className="stack" style={{ gap: 22 }}>
      <div className="page-head">
        <div>
          <h1>Mis recomendaciones</h1>
          <p className="muted">
            Las mejores oportunidades del momento según el modelo, ajustadas a tu perfil. Pulsa una tarjeta para ver por qué.
          </p>
        </div>
        <span className="row small" style={{ gap: 6 }}>
          ¿Cómo se decide la etiqueta? <Help term="model_label" />
        </span>
      </div>

      {error && <ErrorBox error={error} onRetry={reload} />}
      {!data && !error && <Loading height={110} count={2} />}

      {data && (
        <>
          <div className="grid tiles">
            {LABEL_TILES.map((t) => (
              <button
                key={t.key}
                className="card card-link stack tight"
                aria-pressed={label === t.key}
                style={label === t.key ? { borderColor: `var(--${t.key})` } : undefined}
                onClick={() => setLabel(label === t.key ? "all" : t.key)}
              >
                <span className={`row small strong text-${t.key}`} style={{ gap: 8 }}>
                  {t.icon}
                  {t.text}
                </span>
                <span style={{ fontSize: 30, fontWeight: 800 }}>{data.counts[t.key]}</span>
                <span className="muted small">{t.sub}</span>
              </button>
            ))}
            <button className="card card-link stack tight" style={{ background: "var(--accent-soft)", borderColor: "transparent" }} onClick={() => go({ name: "perfil" })}>
              <span className="small strong" style={{ color: "var(--accent-text)" }}>Tu perfil</span>
              <span style={{ fontSize: 22, fontWeight: 800 }}>{data.profile.label}</span>
              <span className="muted small">
                Riesgo hasta {data.profile.max_risk_label} · {data.profile.objective_label} ·{" "}
                <span style={{ color: "var(--accent-text)", fontWeight: 600 }}>Repetir test</span>
              </span>
            </button>
          </div>

          <div className="row wrap" style={{ gap: 8 }}>
            {chip("all", kind, setKind, "Todo")}
            {chip("stock", kind, setKind, "Acciones")}
            {chip("etf", kind, setKind, "ETFs")}
            <span style={{ width: 1, height: 24, background: "var(--border)", margin: "0 6px" }} />
            {chip("all", label, setLabel, "Todas")}
            {chip("buy", label, setLabel, "Comprar")}
            {chip("watch", label, setLabel, "Vigilar")}
            {chip("avoid", label, setLabel, "Evitar")}
            <span style={{ width: 1, height: 24, background: "var(--border)", margin: "0 6px" }} />
            {chip("all", region, setRegion, "Todos los mercados")}
            {chip("es", region, setRegion, "Solo España")}
            <span className="muted small" style={{ marginLeft: "auto" }}>
              {items.length} valores · por señal y puntuación
            </span>
          </div>

          {items.length === 0 ? (
            <div className="empty">Ningún valor cumple estos filtros con tu perfil.</div>
          ) : (
            <div className="grid cards">
              {items.slice(0, limit).map((r) => (
                <RecCard key={r.ticker} r={r} go={go} />
              ))}
            </div>
          )}
          {items.length > limit && (
            <button className="btn" style={{ alignSelf: "center" }} onClick={() => setLimit(limit + PAGE)}>
              Ver más ({items.length - limit} restantes)
            </button>
          )}
          <Stamp source={data.source} at={data.built_at} prefix="Fundamentales y precios:" />
        </>
      )}
    </div>
  );
}
