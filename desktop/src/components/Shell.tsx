// Barra lateral, barra superior (buscador, fuente de datos, tema) y navegación.

import { useEffect, useRef, useState, type ReactNode } from "react";
import { api, useApi } from "../api";
import type { SearchResult, UniverseStatus } from "../types";
import {
  IconBook,
  IconCap,
  IconFlag,
  IconHome,
  IconMoon,
  IconRadar,
  IconRefresh,
  IconSearch,
  IconSliders,
  IconSun,
  IconTarget,
  IconUser,
  IconWallet,
} from "./Icons";
import { Stamp } from "./ui";

export type Page =
  | { name: "inicio" }
  | { name: "recs" }
  | { name: "detalle"; ticker: string }
  | { name: "espana" }
  | { name: "cartera" }
  | { name: "invertir" }
  | { name: "aprender" }
  | { name: "metodologia" }
  | { name: "perfil" }
  | { name: "ajustes" };

const NAV: { name: Page["name"]; label: string; icon: ReactNode; soon?: string }[] = [
  { name: "inicio", label: "Inicio", icon: <IconHome /> },
  { name: "recs", label: "Mis recomendaciones", icon: <IconTarget /> },
  { name: "espana", label: "España", icon: <IconFlag /> },
  { name: "cartera", label: "Mi cartera", icon: <IconWallet />, soon: "Pronto" },
  { name: "invertir", label: "Cómo invertir", icon: <IconBook /> },
  { name: "aprender", label: "Aprender", icon: <IconCap /> },
  { name: "metodologia", label: "Metodología", icon: <IconSliders /> },
];

export function Sidebar({ page, go }: { page: Page; go: (p: Page) => void }) {
  const active = page.name === "detalle" ? "recs" : page.name;
  const item = (name: Page["name"], label: string, icon: ReactNode, soon?: string) => (
    <button
      key={name}
      className={`nav-item${active === name ? " active" : ""}`}
      aria-current={active === name ? "page" : undefined}
      onClick={() => go({ name } as Page)}
    >
      {icon}
      {label}
      {soon && <span className="soon">{soon}</span>}
    </button>
  );
  return (
    <nav className="sidebar" aria-label="Navegación principal">
      <div className="brand">
        <span className="brand-mark">
          <IconRadar />
        </span>
        Radar Bolsa
      </div>
      {NAV.map((n) => item(n.name, n.label, n.icon, n.soon))}
      <div className="nav-spacer" />
      {item("perfil", "Mi perfil inversor", <IconUser />)}
      {item("ajustes", "Ajustes y API keys", <IconSliders />)}
    </nav>
  );
}

function SearchBox({ go }: { go: (p: Page) => void }) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [sel, setSel] = useState(0);
  const [busy, setBusy] = useState(false);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (q.trim().length < 2) {
      setResults([]);
      return;
    }
    const t = setTimeout(() => {
      setBusy(true);
      api<SearchResult[]>(`/api/search?q=${encodeURIComponent(q.trim())}`)
        .then((r) => {
          setResults(r);
          setSel(0);
          setOpen(true);
        })
        .catch(() => setResults([]))
        .finally(() => setBusy(false));
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => !box.current?.contains(e.target as Node) && setOpen(false);
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const pick = (r: SearchResult) => {
    setOpen(false);
    setQ("");
    go({ name: "detalle", ticker: r.ticker });
  };

  return (
    <div className="search" ref={box}>
      <label>
        <IconSearch />
        <span className="visually-hidden">Buscar empresa o ETF</span>
        <input
          type="search"
          value={q}
          placeholder="Busca por nombre o ticker: Iberdrola, Inditex, ASML…"
          role="combobox"
          aria-expanded={open && results.length > 0}
          aria-controls="search-results"
          onChange={(e) => setQ(e.target.value)}
          onFocus={() => results.length && setOpen(true)}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") setSel((s) => Math.min(s + 1, results.length - 1));
            else if (e.key === "ArrowUp") setSel((s) => Math.max(s - 1, 0));
            else if (e.key === "Enter" && results[sel]) pick(results[sel]);
            else if (e.key === "Escape") setOpen(false);
          }}
        />
        {busy && <span className="tiny">Buscando…</span>}
      </label>
      {open && q.trim().length >= 2 && (
        <div className="search-results" id="search-results" role="listbox">
          {results.length === 0 && !busy && <div className="muted small" style={{ padding: 12 }}>Sin resultados.</div>}
          {results.map((r, i) => (
            <button key={r.ticker} role="option" aria-selected={i === sel} onMouseDown={(e) => e.preventDefault()} onClick={() => pick(r)}>
              <span>
                <span className="strong">{r.name}</span>
                <span className="muted small"> · {r.ticker}</span>
              </span>
              <span className="muted tiny">
                {r.quote_type === "ETF" ? "ETF" : "Acción"} · {r.exchange ?? "—"}
                {!r.in_universe && " · fuera del universo"}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function Topbar({ go, theme, toggleTheme, status, onRebuild }: {
  go: (p: Page) => void;
  theme: "light" | "dark";
  toggleTheme: () => void;
  status: UniverseStatus | undefined;
  onRebuild: () => void;
}) {
  const b = status?.build;
  return (
    <header className="topbar">
      <SearchBox go={go} />
      {b?.running ? (
        <span className="stamp" aria-live="polite">
          <IconRefresh /> Actualizando datos… {b.done}/{b.total || "…"}
        </span>
      ) : status?.built_at ? (
        <button className="btn small" style={{ border: 0, background: "transparent", padding: 0 }} onClick={onRebuild} title="Pulsa para volver a descargar los datos">
          <Stamp source={status.source} at={status.built_at} stale={status.stale} prefix="Datos:" />
          <IconRefresh />
        </button>
      ) : null}
      <button className="btn icon-btn" aria-label={theme === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro"} onClick={toggleTheme}>
        {theme === "dark" ? <IconSun /> : <IconMoon />}
      </button>
    </header>
  );
}

/** Estado del universo, consultado cada pocos segundos mientras se reconstruye. */
export function useUniverseStatus() {
  const { data, reload } = useApi<UniverseStatus>("/api/universe/status");
  const running = data?.build.running;
  useEffect(() => {
    if (!running) return;
    const t = setInterval(reload, 1500);
    return () => clearInterval(t);
  }, [running, reload]);
  return { status: data, reload };
}
