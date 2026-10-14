import { useCallback, useEffect, useRef, useState } from "react";
import { api, invalidate, useApi } from "./api";
import { IconRadar } from "./components/Icons";
import { Sidebar, Topbar, useUniverseStatus, type Page } from "./components/Shell";
import { Disclaimer, ErrorBox, GlossaryProvider } from "./components/ui";
import { Detalle } from "./pages/Detalle";
import { Espana } from "./pages/Espana";
import { Ajustes, Aprender, Inicio, Proximamente } from "./pages/Otras";
import { Invertir } from "./pages/Invertir";
import { Metodologia } from "./pages/Metodologia";
import { Perfil } from "./pages/Perfil";
import { Recomendaciones } from "./pages/Recomendaciones";
import type { Answers } from "./types";

type Theme = "light" | "dark";

// La pantalla actual vive en el hash (#/espana, #/detalle/IBE.MC): permite volver atrás.
function pageFromHash(): Page {
  const [name, arg] = window.location.hash.replace(/^#\/?/, "").split("/");
  if (name === "detalle" && arg) return { name: "detalle", ticker: decodeURIComponent(arg) };
  const simple = ["inicio", "recs", "espana", "cartera", "invertir", "aprender", "metodologia", "perfil", "ajustes"];
  return simple.includes(name) ? ({ name } as Page) : { name: "recs" };
}

function hashFor(p: Page): string {
  return p.name === "detalle" ? `#/detalle/${encodeURIComponent(p.ticker)}` : `#/${p.name}`;
}

function initialTheme(): Theme {
  try {
    const saved = localStorage.getItem("theme");
    if (saved === "light" || saved === "dark") return saved;
  } catch {
    /* sin almacenamiento: se usa el del sistema */
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/** Pantalla de primera descarga de datos (o mientras se actualizan sin datos previos). */
function FirstBuild({ done, total, error, onRetry }: { done: number; total: number; error: string | null; onRetry: () => void }) {
  return (
    <div className="card stack" style={{ maxWidth: 620, margin: "8vh auto", padding: 32, gap: 18 }}>
      <span className="brand-mark" style={{ width: 48, height: 48 }}><IconRadar size={26} /></span>
      <h1>Preparando los datos</h1>
      <p className="muted" style={{ lineHeight: 1.55 }}>
        La primera vez, la app descarga de Yahoo Finance los fundamentales y el histórico de unos 225 valores (IBEX 35, Mercado Continuo, Euro Stoxx 50, grandes de EE. UU. y ETFs). Tarda alrededor de un minuto; después se guardan en este ordenador.
      </p>
      <div className="progress" aria-label="Progreso de la descarga"><div style={{ width: `${total ? (done / total) * 100 : 3}%` }} /></div>
      <span className="small muted" aria-live="polite">{total ? `${done} de ${total} valores` : "Empezando…"}</span>
      {error && (
        <div className="error-box stack">
          {error}
          <button className="btn small" onClick={onRetry}>Reintentar</button>
        </div>
      )}
    </div>
  );
}

export function App() {
  const [theme, setTheme] = useState<Theme>(initialTheme);
  const [page, setPage] = useState<Page>(pageFromHash);
  const profile = useApi<{ answers: Answers | null }>("/api/profile");
  const { status, reload: reloadStatus } = useUniverseStatus();
  const main = useRef<HTMLElement>(null);
  const wasRunning = useRef(false);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  // Solo se recuerda si el usuario lo cambia a mano; si no, se sigue al sistema.
  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    try {
      localStorage.setItem("theme", next);
    } catch {
      /* ignorado */
    }
  };

  const rebuild = useCallback(async () => {
    await api("/api/universe/build", { method: "POST" }).catch(() => undefined);
    reloadStatus();
  }, [reloadStatus]);

  // Primera ejecución: sin datos, se lanza la descarga mientras el usuario hace el test.
  useEffect(() => {
    if (status && status.rows === 0 && !status.build.running && !status.build.error) rebuild();
  }, [status, rebuild]);

  // Al terminar una actualización, se vuelven a pedir todas las pantallas.
  useEffect(() => {
    const running = !!status?.build.running;
    if (wasRunning.current && !running) invalidate("/api/");
    wasRunning.current = running;
  }, [status?.build.running]);

  useEffect(() => {
    const onHash = () => setPage(pageFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const go = useCallback((p: Page) => {
    if (window.location.hash !== hashFor(p)) window.location.hash = hashFor(p);
    setPage(p);
    main.current?.scrollTo({ top: 0 });
  }, []);

  if (profile.error && profile.error.code === "engine") {
    return <div style={{ padding: 32 }}><ErrorBox error={profile.error} /></div>;
  }
  if (!profile.data || !status) {
    return (
      <div style={{ display: "grid", placeItems: "center", height: "100%" }} className="muted">
        <span className="row"><IconRadar /> Arrancando el motor de datos…</span>
      </div>
    );
  }

  const firstTime = profile.data.answers == null;
  if (firstTime) {
    return (
      <main className="main" style={{ padding: "28px 16px" }}>
        <div className="brand" style={{ justifyContent: "center", paddingBottom: 24 }}>
          <span className="brand-mark"><IconRadar /></span>
          Radar Bolsa
        </div>
        <GlossaryProvider>
          <Perfil firstTime onDone={() => { profile.reload(); go({ name: "recs" }); }} />
        </GlossaryProvider>
      </main>
    );
  }

  const needsData = status.rows === 0 && page.name !== "perfil" && page.name !== "ajustes" && page.name !== "aprender";

  let body;
  if (needsData) body = <FirstBuild done={status.build.done} total={status.build.total} error={status.build.error} onRetry={rebuild} />;
  else if (page.name === "inicio") body = <Inicio go={go} status={status} />;
  else if (page.name === "recs") body = <Recomendaciones go={go} />;
  else if (page.name === "detalle") body = <Detalle key={page.ticker} ticker={page.ticker} go={go} />;
  else if (page.name === "espana") body = <Espana go={go} />;
  else if (page.name === "perfil") body = <Perfil firstTime={false} onDone={() => { profile.reload(); go({ name: "recs" }); }} />;
  else if (page.name === "ajustes") body = <Ajustes status={status} onRebuild={rebuild} />;
  else if (page.name === "aprender") body = <Aprender />;
  else if (page.name === "metodologia") body = <Metodologia />;
  else if (page.name === "cartera")
    body = <Proximamente title="Mi cartera" text="La cartera simulada (operaciones, valoración en euros y comparación con un índice) y las alertas con notificaciones de escritorio llegan en la fase 4. Mientras tanto siguen disponibles en la versión anterior (Streamlit)." />;
  else body = <Invertir />;

  return (
    <GlossaryProvider>
      <div className="shell">
        <Sidebar page={page} go={go} />
        <main className="main" ref={main}>
          <Topbar go={go} theme={theme} toggleTheme={toggleTheme} status={status} onRebuild={rebuild} />
          <div className="content">{body}</div>
          <Disclaimer />
        </main>
      </div>
    </GlossaryProvider>
  );
}
