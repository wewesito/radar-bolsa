import { useEffect, useState } from "react";
import { api } from "../api";
import { fmtMoney, fmtNum, fmtPct } from "../format";

type Compound = {
  rows: { year: number; contributed: number; value: number }[];
  gain: number;
  real_return: number;
  real_value: number;
};
type Tax = { base: number; tax: number; effective_rate: number };

const inputStyle = { height: 42, borderRadius: 10, border: "1px solid var(--border)", background: "var(--surface2)", color: "var(--text)", padding: "0 12px", font: "inherit", width: "100%" } as const;

function Field({ label, value, onChange, step = 1, suffix }: { label: string; value: number; onChange: (v: number) => void; step?: number; suffix?: string }) {
  return (
    <label className="stack tight" style={{ flex: "1 1 150px" }}>
      <span className="small strong">{label}{suffix ? ` (${suffix})` : ""}</span>
      <input type="number" inputMode="decimal" min={0} step={step} value={Number.isFinite(value) ? value : ""} onChange={(e) => onChange(e.target.value === "" ? NaN : Number(e.target.value))} style={inputStyle} />
    </label>
  );
}

function GrowthChart({ rows }: { rows: Compound["rows"] }) {
  const W = 640, H = 220, P = { t: 10, r: 10, b: 22, l: 56 };
  const max = Math.max(...rows.map((r) => r.value), 1);
  const x = (i: number) => P.l + (i / Math.max(rows.length - 1, 1)) * (W - P.l - P.r);
  const y = (v: number) => P.t + (1 - v / max) * (H - P.t - P.b);
  const line = (k: "value" | "contributed") => rows.map((r, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(r[k]).toFixed(1)}`).join("");
  const end = rows[rows.length - 1];
  return (
    <div className="stack tight">
      <svg role="img" aria-label={`Tras ${end.year} años: aportado ${fmtMoney(end.contributed, "EUR")}, valor ${fmtMoney(end.value, "EUR")}`} viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "auto" }}>
        {[0, 0.5, 1].map((f) => (
          <g key={f}>
            <line x1={P.l} x2={W - P.r} y1={y(max * f)} y2={y(max * f)} stroke="var(--border)" />
            <text x={P.l - 6} y={y(max * f) + 4} textAnchor="end" fontSize="11" fill="var(--muted)">{fmtNum(max * f, 0)}</text>
          </g>
        ))}
        <text x={P.l} y={H - 5} fontSize="11" fill="var(--muted)">Año 0</text>
        <text x={W - P.r} y={H - 5} textAnchor="end" fontSize="11" fill="var(--muted)">Año {end.year}</text>
        <path d={line("contributed")} fill="none" stroke="var(--muted)" strokeWidth="2" strokeDasharray="6 4" />
        <path d={line("value")} fill="none" stroke="var(--chart)" strokeWidth="2.6" />
      </svg>
      <div className="row wrap small">
        <span className="row" style={{ gap: 6 }}><svg width="28" height="8" aria-hidden="true"><line x1="0" x2="28" y1="4" y2="4" stroke="var(--chart)" strokeWidth="2.6" /></svg>Valor de la inversión (€)</span>
        <span className="row" style={{ gap: 6 }}><svg width="28" height="8" aria-hidden="true"><line x1="0" x2="28" y1="4" y2="4" stroke="var(--muted)" strokeWidth="2" strokeDasharray="6 4" /></svg>Dinero aportado (€)</span>
      </div>
    </div>
  );
}

export function CompoundCalculator() {
  const [v, setV] = useState({ initial: 5000, monthly: 200, ret: 6, years: 20, fee: 0.2, infl: 2 });
  const [res, setRes] = useState<Compound | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const set = (k: keyof typeof v) => (n: number) => setV((o) => ({ ...o, [k]: n }));

  useEffect(() => {
    if (Object.values(v).some((n) => !Number.isFinite(n))) return;
    const q = new URLSearchParams({
      initial: String(v.initial), monthly: String(v.monthly), annual_return: String(v.ret / 100),
      years: String(Math.round(v.years)), fee: String(v.fee / 100), inflation: String(v.infl / 100),
    });
    const id = setTimeout(() => {
      api<Compound>(`/api/calc/compound?${q}`).then((r) => { setRes(r); setErr(null); }).catch((e: Error) => setErr(e.message));
    }, 250);
    return () => clearTimeout(id);
  }, [v]);

  const end = res?.rows[res.rows.length - 1];
  return (
    <section className="card stack" aria-labelledby="calc-compound">
      <h2 id="calc-compound">Calculadora de interés compuesto</h2>
      <p className="small muted" style={{ lineHeight: 1.5 }}>
        Simulación con una rentabilidad constante que tú eliges. Es un ejemplo para entender el efecto del tiempo y de las comisiones, no una predicción: la rentabilidad real varía cada año y puede ser negativa.
      </p>
      <div className="row wrap" style={{ alignItems: "flex-end" }}>
        <Field label="Inversión inicial" suffix="€" value={v.initial} onChange={set("initial")} step={500} />
        <Field label="Aportación mensual" suffix="€" value={v.monthly} onChange={set("monthly")} step={50} />
        <Field label="Años" value={v.years} onChange={set("years")} />
      </div>
      <div className="row wrap" style={{ alignItems: "flex-end" }}>
        <Field label="Rentabilidad anual" suffix="%" value={v.ret} onChange={set("ret")} step={0.5} />
        <Field label="Comisión anual" suffix="%" value={v.fee} onChange={set("fee")} step={0.1} />
        <Field label="Inflación anual" suffix="%" value={v.infl} onChange={set("infl")} step={0.5} />
      </div>
      {err && <div className="error-box small">{err}</div>}
      {res && end && (
        <div className="stack" aria-live="polite">
          <div className="row wrap" style={{ gap: 24 }}>
            <div><div className="tiny muted">Aportado</div><div className="strong" style={{ fontSize: 20 }}>{fmtMoney(end.contributed, "EUR")}</div></div>
            <div><div className="tiny muted">Valor final</div><div className="strong" style={{ fontSize: 20 }}>{fmtMoney(end.value, "EUR")}</div></div>
            <div><div className="tiny muted">Ganancia</div><div className="strong" style={{ fontSize: 20 }}>{fmtMoney(res.gain, "EUR")}</div></div>
            <div><div className="tiny muted">Valor final en euros de hoy</div><div className="strong" style={{ fontSize: 20 }}>{fmtMoney(res.real_value, "EUR")}</div></div>
          </div>
          <p className="tiny muted">Rentabilidad real anual (neta de comisión e inflación): {fmtPct(res.real_return, 2)}. Antes de impuestos.</p>
          <GrowthChart rows={res.rows} />
        </div>
      )}
    </section>
  );
}

export function TaxCalculator() {
  const [base, setBase] = useState(10000);
  const [res, setRes] = useState<Tax | null>(null);
  useEffect(() => {
    if (!Number.isFinite(base)) return;
    const id = setTimeout(() => {
      api<Tax>(`/api/calc/tax?base=${base}`).then(setRes).catch(() => setRes(null));
    }, 250);
    return () => clearTimeout(id);
  }, [base]);
  return (
    <section className="card stack" aria-labelledby="calc-tax">
      <h2 id="calc-tax">Calculadora de impuestos del ahorro</h2>
      <p className="small muted" style={{ lineHeight: 1.5 }}>
        Cuota aproximada del IRPF sobre ganancias, dividendos e intereses netos (tramos generales). Orientativa: comprueba la normativa vigente en la AEAT.
      </p>
      <div style={{ maxWidth: 260 }}><Field label="Ganancia anual neta" suffix="€" value={base} onChange={setBase} step={500} /></div>
      {res && (
        <p aria-live="polite" style={{ lineHeight: 1.6 }}>
          Pagarías unos <strong>{fmtMoney(res.tax, "EUR")}</strong> ({fmtPct(res.effective_rate, 1)} de media) y te quedarían <strong>{fmtMoney(res.base - res.tax, "EUR")}</strong>.
        </p>
      )}
    </section>
  );
}
