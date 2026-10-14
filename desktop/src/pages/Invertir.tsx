import { useState } from "react";
import { useApi } from "../api";
import { CompoundCalculator, TaxCalculator } from "../components/Calculators";
import { Markdown } from "../components/Markdown";
import { ErrorBox, Loading } from "../components/ui";
import type { GuidesData } from "../types";

export function Invertir() {
  const { data, error, reload } = useApi<GuidesData>("/api/guides");
  const [key, setKey] = useState("broker");
  const guide = data?.guides.find((g) => g.key === key);
  return (
    <div className="stack" style={{ gap: 20, maxWidth: 920 }}>
      <div>
        <h1>Cómo invertir</h1>
        <p className="muted" style={{ marginTop: 6, lineHeight: 1.55 }}>
          Guías paso a paso para pasar de la señal del modelo a una compra real. Información general y educativa, no asesoramiento.
        </p>
      </div>
      {error && <ErrorBox error={error} onRetry={reload} />}
      {!data && !error && <Loading height={200} />}
      {data && (
        <>
          <div className="row wrap" style={{ gap: 8 }} role="tablist" aria-label="Guías">
            {data.guides.map((g) => (
              <button key={g.key} role="tab" aria-selected={key === g.key} className="chip small" aria-pressed={key === g.key} onClick={() => setKey(g.key)}>{g.title}</button>
            ))}
          </div>
          {guide && (
            <article className="card stack" role="tabpanel">
              <h2>{guide.title}</h2>
              <p className="muted small">{guide.summary}</p>
              <Markdown text={guide.body} />
            </article>
          )}
          {key === "aportaciones" && <CompoundCalculator />}
          {key === "fiscalidad" && <TaxCalculator />}
        </>
      )}
    </div>
  );
}
