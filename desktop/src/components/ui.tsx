import { createContext, useContext, useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { useApi, type ApiError } from "../api";
import { fmtAge, fmtDateTime, fmtMoney } from "../format";
import type { GlossaryEntry, Label } from "../types";
import { IconBan, IconCheckCircle, IconEye, IconInfo, IconShield, IconX } from "./Icons";

// --- Semáforo: siempre color + icono + texto -----------------------------------------

const LABEL_TEXT: Record<Label, string> = { buy: "Comprar", watch: "Vigilar", avoid: "Evitar" };

export function LabelIcon({ label, size }: { label: Label; size?: number }) {
  if (label === "buy") return <IconCheckCircle size={size} />;
  if (label === "watch") return <IconEye size={size} />;
  return <IconBan size={size} />;
}

export function LabelPill({ label, large }: { label: Label; large?: boolean }) {
  return (
    <span className={`pill tone-${label}${large ? " lg" : ""}`}>
      <LabelIcon label={label} size={large ? 20 : 15} />
      {LABEL_TEXT[label]}
    </span>
  );
}

const RISK_TONE = ["buy", "watch", "avoid"] as const;
const RISK_TEXT = ["Bajo", "Medio", "Alto"];

export function RiskPill({ level }: { level: number | null }) {
  if (level == null) return <span className="pill tone-neutral">n/d</span>;
  return <span className={`pill tone-${RISK_TONE[level]}`}>{RISK_TEXT[level]}</span>;
}

export function scoreTone(score: number | null | undefined): Label | "neutral" {
  if (score == null) return "neutral";
  return score >= 65 ? "buy" : score >= 45 ? "watch" : "avoid";
}

export function ScoreBar({ score, tone }: { score: number | null; tone?: string }) {
  const t = tone ?? scoreTone(score);
  return (
    <div className="bar" role="img" aria-label={score == null ? "Sin puntuación" : `${Math.round(score)} de 100`}>
      <div style={{ width: `${score ?? 0}%`, background: `var(--${t === "neutral" ? "muted" : t})` }} />
    </div>
  );
}

/** Barra del rango de entrada con la marca del precio actual. */
export function RangeBar({
  low,
  high,
  price,
  currency,
  showLabel,
}: {
  low: number;
  high: number;
  price: number | null;
  currency: string | null;
  showLabel?: boolean;
}) {
  // Escala: el rango ocupa el centro; el precio se coloca dentro del 0–100 %
  const span = Math.max(high - low, high * 0.02);
  const min = low - span * 0.75;
  const max = high + span * 0.75;
  const pos = (v: number) => Math.min(100, Math.max(0, ((v - min) / (max - min)) * 100));
  return (
    <div style={{ paddingBottom: showLabel ? 20 : 0 }}>
      <div className="range-track" role="img" aria-label={`Rango de ${fmtMoney(low, currency)} a ${fmtMoney(high, currency)}; precio ${fmtMoney(price, currency)}`}>
        <div className="range-zone" style={{ left: `${pos(low)}%`, width: `${Math.max(pos(high) - pos(low), 2)}%` }} />
        {price != null && (
          <div className="range-mark" style={{ left: `${pos(price)}%` }}>
            {showLabel && (
              <span className="tiny strong" style={{ position: "absolute", top: 20, left: "50%", transform: "translateX(-50%)", whiteSpace: "nowrap" }}>
                Hoy {fmtMoney(price, currency)}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// --- Fuente y fecha ------------------------------------------------------------------

export function Stamp({ source, at, delay, stale, prefix }: { source: string; at: string | null | undefined; delay?: number | null; stale?: boolean; prefix?: string }) {
  return (
    <span className="stamp" title={at ? `${fmtDateTime(at)} (${fmtAge(at)})` : undefined}>
      <span className={`dot${stale ? " stale" : ""}`} />
      {prefix ? `${prefix} ` : ""}
      {source} · {fmtDateTime(at)}
      {delay ? ` · retraso ~${delay} min` : ""}
      {stale ? " · copia antigua (la fuente no respondió)" : ""}
    </span>
  );
}

export function Disclaimer() {
  return (
    <footer className="footer">
      <div className="disclaimer">
        <IconInfo />
        <span>
          Las recomendaciones las genera un modelo propio a partir de datos públicos. No garantizan rentabilidad y no
          sustituyen a un asesor financiero.
        </span>
      </div>
    </footer>
  );
}

// --- Estados ---------------------------------------------------------------------------

export function Loading({ height = 160, count = 1 }: { height?: number; count?: number }) {
  return (
    <>
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="skeleton" style={{ height }} aria-hidden="true" />
      ))}
      <span className="visually-hidden">Cargando…</span>
    </>
  );
}

export function ErrorBox({ error, onRetry }: { error: ApiError | Error; onRetry?: () => void }) {
  return (
    <div className="error-box stack" role="alert" style={{ alignItems: "center" }}>
      <strong>No se han podido cargar los datos</strong>
      <span className="muted">{error.message}</span>
      {onRetry && (
        <button className="btn small" onClick={onRetry}>
          Reintentar
        </button>
      )}
    </div>
  );
}

export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return createPortal(
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" role="dialog" aria-modal="true" aria-label={title} onClick={(e) => e.stopPropagation()}>
        <div className="row between">
          <h2>{title}</h2>
          <button className="btn icon-btn" aria-label="Cerrar" onClick={onClose}>
            <IconX />
          </button>
        </div>
        {children}
      </div>
    </div>,
    document.body,
  );
}

// --- Ayuda "?" ---------------------------------------------------------------------------

type GlossaryData = { entries: GlossaryEntry[]; components: { key: string; label: string; description: string }[] };
const GlossaryCtx = createContext<Map<string, GlossaryEntry>>(new Map());

export function GlossaryProvider({ children }: { children: ReactNode }) {
  const { data } = useApi<GlossaryData>("/api/glossary");
  const map = new Map((data?.entries ?? []).map((e) => [e.key, e]));
  return <GlossaryCtx.Provider value={map}>{children}</GlossaryCtx.Provider>;
}

export function useGlossary() {
  return useContext(GlossaryCtx);
}

/** Icono "?" con una explicación sencilla. `term` = clave del glosario o texto propio. */
export function Help({ term, title, text }: { term?: string; title?: string; text?: string }) {
  const glossary = useGlossary();
  const entry = term ? glossary.get(term) : undefined;
  const [open, setOpen] = useState(false);
  const btn = useRef<HTMLButtonElement>(null);
  const [pos, setPos] = useState({ top: 0, left: 0 });

  useLayoutEffect(() => {
    if (!open || !btn.current) return;
    const r = btn.current.getBoundingClientRect();
    const width = 340;
    const left = Math.min(Math.max(16, r.left - width / 2), window.innerWidth - width - 16);
    const below = r.bottom + 8;
    setPos({ top: below + 220 > window.innerHeight ? Math.max(16, r.top - 230) : below, left });
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const close = () => setOpen(false);
    window.addEventListener("scroll", close, true);
    window.addEventListener("resize", close);
    return () => {
      window.removeEventListener("scroll", close, true);
      window.removeEventListener("resize", close);
    };
  }, [open]);

  const heading = title ?? entry?.term ?? "Ayuda";
  if (!entry && !text) return null;
  return (
    <>
      <button
        ref={btn}
        type="button"
        className="help"
        aria-label={`Qué es: ${heading}`}
        aria-expanded={open}
        onClick={(e) => {
          e.stopPropagation();
          setOpen((o) => !o);
        }}
        onBlur={() => setOpen(false)}
      >
        ?
      </button>
      {open &&
        createPortal(
          <div className="popover" role="tooltip" style={pos}>
            <h4>{heading}</h4>
            {text && <p>{text}</p>}
            {entry && (
              <>
                <p>{entry.what}</p>
                <p className="muted">
                  <strong>Cómo leerlo:</strong> {entry.reading}
                </p>
                <p className="muted">
                  <strong>Ojo:</strong> {entry.limits}
                </p>
              </>
            )}
          </div>,
          document.body,
        )}
    </>
  );
}

export function RiskIcon() {
  return <IconShield />;
}
