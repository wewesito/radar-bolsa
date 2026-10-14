import { useMemo, useState } from "react";
import { useApi } from "../api";
import type { Page } from "../components/Shell";
import { ErrorBox, Help, LabelPill, Loading, Stamp } from "../components/ui";
import { fmtBig, fmtNum, fmtPct } from "../format";
import type { SpainData, SpainRow } from "../types";

type Fmt = "pct" | "spct" | "x" | "int" | "tag" | "big";
type Col = { key: string; label: string; fmt: Fmt; help?: string; helpText?: string };

const TABS: { id: string; label: string; note: string; cols: Col[]; defaultSort: string }[] = [
  {
    id: "bolsa",
    label: "En bolsa",
    note: "Cuánto ha ganado o perdido la acción. La rentabilidad total suma los dividendos reinvertidos.",
    defaultSort: "ret_1y",
    cols: [
      { key: "ret_ytd", label: "En el año", fmt: "spct", help: "ret_ytd" },
      { key: "ret_1y", label: "1 año", fmt: "spct", help: "ret_1y" },
      { key: "ret_3y", label: "3 años", fmt: "spct", help: "ret_3y" },
      { key: "ret_5y", label: "5 años", fmt: "spct", help: "ret_5y" },
      { key: "tr_1y", label: "Total 1 año", fmt: "spct", help: "tr_1y" },
      { key: "tr_5y", label: "Total 5 años", fmt: "spct", help: "tr_5y" },
    ],
  },
  {
    id: "negocio",
    label: "Negocio",
    note: "Cuánto gana la empresa con lo que tiene y cómo crecen sus beneficios.",
    defaultSort: "roe",
    cols: [
      { key: "roe", label: "ROE", fmt: "pct", help: "roe" },
      { key: "roic", label: "ROIC", fmt: "pct", help: "roic" },
      { key: "operating_margin", label: "Margen operativo", fmt: "pct", help: "operating_margin" },
      { key: "profit_margin", label: "Margen neto", fmt: "pct", help: "profit_margin" },
      { key: "earnings_growth", label: "Crec. beneficio", fmt: "spct", help: "earnings_growth" },
    ],
  },
  {
    id: "dividendo",
    label: "Dividendo",
    note: "Cuánto reparte, desde cuándo y si lo puede mantener.",
    defaultSort: "dividend_yield",
    cols: [
      { key: "dividend_yield", label: "Rentabilidad", fmt: "pct", help: "dividend_yield" },
      { key: "div_years", label: "Años seguidos", fmt: "int", help: "div_years" },
      { key: "payout_ratio", label: "Payout", fmt: "pct", help: "payout_ratio" },
      {
        key: "div_sustainability",
        label: "Sostenibilidad",
        fmt: "tag",
        helpText:
          "Alta: reparte como mucho el 70 % del beneficio y lleva 5 años o más pagando. Baja: reparte más de lo que gana o está en pérdidas. Media: el resto.",
      },
    ],
  },
  {
    id: "valoracion",
    label: "Valoración",
    note: "Si cotiza cara o barata frente a las empresas de su sector.",
    defaultSort: "pe_trailing",
    cols: [
      { key: "pe_trailing", label: "PER", fmt: "x", help: "pe_trailing" },
      { key: "pe_sector", label: "PER sector", fmt: "x" },
      { key: "price_to_book", label: "P/VC", fmt: "x", help: "price_to_book" },
      { key: "pb_sector", label: "P/VC sector", fmt: "x" },
      {
        key: "valuation_reading",
        label: "Lectura",
        fmt: "tag",
        helpText: "Barata: PER más de un 15 % por debajo de la mediana de su sector. Cara: más de un 15 % por encima.",
      },
      { key: "market_cap", label: "Capitalización", fmt: "big", help: "market_cap" },
    ],
  },
];

const TAG_TONE: Record<string, string> = {
  Alta: "buy",
  Media: "watch",
  Baja: "avoid",
  "Barata vs. sector": "buy",
  "En línea": "watch",
  "Cara vs. sector": "avoid",
};

function cell(v: number | string | boolean | null, fmt: Fmt, currency: string | null) {
  if (fmt === "tag") {
    if (v == null) return <span className="muted">n/d</span>;
    const tone = TAG_TONE[String(v)];
    return tone ? <span className={`pill tone-${tone}`} style={{ height: 24 }}>{v}</span> : <span className="muted">{v}</span>;
  }
  const n = typeof v === "number" ? v : null;
  if (fmt === "spct") return <span className={n == null ? "muted" : n >= 0 ? "up" : "down"}>{fmtPct(n, 1, true)}</span>;
  if (fmt === "pct") return fmtPct(n);
  if (fmt === "int") return n == null ? "n/d" : fmtNum(n, 0);
  if (fmt === "big") return fmtBig(n, currency);
  return fmtNum(n, 1);
}

function Top10({ rows, go }: { rows: SpainRow[]; go: (p: Page) => void }) {
  return (
    <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(330px, 1fr))", gap: 14 }}>
      {rows.slice(0, 10).map((r, i) => (
        <button key={r.ticker} className="card card-link row" style={{ gap: 14, padding: "16px 18px" }} onClick={() => go({ name: "detalle", ticker: r.ticker })}>
          <span style={{ width: 38, height: 38, borderRadius: 12, display: "grid", placeItems: "center", fontWeight: 800, fontSize: 16, background: "var(--surface2)", flexShrink: 0 }}>
            {i + 1}
          </span>
          <span className="stack tight" style={{ flex: 1, minWidth: 0, gap: 4 }}>
            <span className="row between" style={{ gap: 8 }}>
              <span className="strong" style={{ fontSize: 16 }}>{r.name}</span>
              {r.label && <LabelPill label={r.label} />}
            </span>
            <span className="tiny muted">{r.ticker} · {r.sector_es} · {r.spain_index}</span>
            <span className="row small muted wrap" style={{ gap: 12, marginTop: 4 }}>
              <span>Puntuación <strong style={{ color: "var(--text)" }}>{r.score == null ? "—" : Math.round(r.score)}</strong></span>
              <span>1 año {cell(r.ret_1y, "spct", null)}</span>
              <span>ROE <strong style={{ color: "var(--text)" }}>{fmtPct(r.roe as number | null)}</strong></span>
              <span>Div. <strong style={{ color: "var(--text)" }}>{fmtPct(r.dividend_yield as number | null)}</strong></span>
            </span>
          </span>
        </button>
      ))}
    </div>
  );
}

export function Espana({ go }: { go: (p: Page) => void }) {
  const { data, error, reload } = useApi<SpainData>("/api/spain");
  const [idx, setIdx] = useState<"all" | "IBEX 35" | "Mercado Continuo">("all");
  const [tab, setTab] = useState("top");
  const [sector, setSector] = useState("Todos");
  const [sort, setSort] = useState<{ key: string; dir: 1 | -1 } | null>(null);

  const filtered = useMemo(
    () => (data?.items ?? []).filter((r) => (idx === "all" || r.spain_index === idx) && (sector === "Todos" || r.sector_es === sector)),
    [data, idx, sector],
  );
  const sectors = useMemo(
    () => ["Todos", ...[...new Set((data?.items ?? []).map((r) => r.sector_es))].sort((a, b) => (a ?? "").localeCompare(b ?? "", "es"))],
    [data],
  );
  const def = TABS.find((t) => t.id === tab);
  const sorted = useMemo(() => {
    if (!def) return filtered;
    const s = sort ?? { key: def.defaultSort, dir: def.defaultSort === "pe_trailing" ? 1 : -1 };
    return [...filtered].sort((a, b) => {
      const va = a[s.key];
      const vb = b[s.key];
      if (va == null) return 1;
      if (vb == null) return -1;
      if (s.key === "pe_trailing" && (va as number) <= 0) return 1; // PER negativo = pérdidas: al final
      if (s.key === "pe_trailing" && (vb as number) <= 0) return -1;
      return (va > vb ? 1 : va < vb ? -1 : 0) * s.dir;
    });
  }, [filtered, def, sort]);

  const activeSort = def ? sort ?? { key: def.defaultSort, dir: def.defaultSort === "pe_trailing" ? 1 : -1 } : null;

  return (
    <div className="stack" style={{ gap: 20 }}>
      <div className="page-head">
        <div>
          <h1>España</h1>
          <p className="muted">Las empresas más rentables del IBEX 35 y el Mercado Continuo: en bolsa, como negocio, por dividendo y por valoración.</p>
        </div>
        <div className="segmented" role="group" aria-label="Índice">
          {(["IBEX 35", "Mercado Continuo", "all"] as const).map((v) => (
            <button key={v} aria-pressed={idx === v} onClick={() => setIdx(v)}>{v === "all" ? "Todos" : v}</button>
          ))}
        </div>
      </div>

      <div className="tabs" role="tablist" aria-label="Ranking">
        {[{ id: "top", label: "Top 10 España" }, ...TABS].map((t) => (
          <button key={t.id} role="tab" aria-selected={tab === t.id} onClick={() => { setTab(t.id); setSort(null); }}>
            {t.label}
          </button>
        ))}
      </div>

      <div className="row wrap" style={{ gap: 8 }}>
        <span className="small strong muted" style={{ marginRight: 4 }}>Sector</span>
        {sectors.map((s) => (
          <button key={s} className="chip small" aria-pressed={sector === s} onClick={() => setSector(s)}>{s}</button>
        ))}
      </div>

      {error && <ErrorBox error={error} onRetry={reload} />}
      {!data && !error && <Loading height={120} count={3} />}

      {data && data.profile_is_default && (
        <div className="card soft small">
          Las señales usan un perfil moderado de referencia porque aún no has hecho el test. <a onClick={() => go({ name: "perfil" })}>Hacer el test</a>
        </div>
      )}

      {data && tab === "top" && (
        <div className="stack">
          <p className="muted small">
            Top 10 combinado: ordenado por la puntuación de la app (valoración, salud, crecimiento, momentum y riesgo frente a su sector) con tu perfil {data.profile_label}. Solo entran empresas que cotizan con normalidad, ganan dinero y valen al menos 200 millones en bolsa. <Help term="score" />
          </p>
          {filtered.some((r) => r.top_eligible) ? (
            <Top10 rows={filtered.filter((r) => r.top_eligible)} go={go} />
          ) : (
            <div className="empty">Sin empresas con estos filtros.</div>
          )}
        </div>
      )}

      {data && def && (
        <div className="stack tight">
          <p className="muted small">{def.note} Pulsa una columna para ordenar y una fila para ver el detalle.</p>
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th className="left">Empresa</th>
                  <th className="left">Sector</th>
                  {def.cols.map((c) => {
                    const on = activeSort?.key === c.key;
                    return (
                      <th key={c.key} aria-sort={on ? (activeSort!.dir < 0 ? "descending" : "ascending") : "none"}>
                        <span className="row" style={{ gap: 6, justifyContent: "flex-end" }}>
                          <button onClick={() => setSort({ key: c.key, dir: on ? (activeSort!.dir === 1 ? -1 : 1) : -1 })}>
                            {c.label} {on ? (activeSort!.dir < 0 ? "↓" : "↑") : ""}
                          </button>
                          {(c.help || c.helpText) && <Help term={c.help} title={c.label} text={c.helpText} />}
                        </span>
                      </th>
                    );
                  })}
                  <th>Señal</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((r) => (
                  <tr key={r.ticker} onClick={() => go({ name: "detalle", ticker: r.ticker })}>
                    <td>
                      <span className="strong">{r.name}</span> <span className="muted small">{r.ticker.replace(".MC", "")}</span>
                    </td>
                    <td className="left muted">{r.sector_es}</td>
                    {def.cols.map((c) => (
                      <td key={c.key}>{cell(r[c.key], c.fmt, r.currency)}</td>
                    ))}
                    <td>{r.label ? <LabelPill label={r.label} /> : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {data && (
        <p className="tiny muted" style={{ lineHeight: 1.6 }}>
          <Stamp source={data.source} at={data.built_at} prefix="Datos:" /> · Tickers de la Bolsa de Madrid (sufijo .MC). {data.items.length} empresas con datos.
          Las medianas del sector usan sus comparables europeos (mismo criterio que la puntuación). Las rentabilidades a 5 años y el historial de dividendos parten, como pronto, de 2000.
        </p>
      )}
    </div>
  );
}
