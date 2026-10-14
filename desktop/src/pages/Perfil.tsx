import { useState } from "react";
import { api, invalidate, useApi } from "../api";
import { ErrorBox, Loading } from "../components/ui";
import type { Answers, Profile, Question } from "../types";

type ProfileResp = { answers: Answers | null; profile: Profile | null };

export function Perfil({ onDone, firstTime }: { onDone: () => void; firstTime: boolean }) {
  const questions = useApi<Question[]>("/api/profile/questions");
  const current = useApi<ProfileResp>("/api/profile");
  const [step, setStep] = useState(firstTime ? 0 : -1); // -1 = ver el perfil actual
  const [answers, setAnswers] = useState<Partial<Answers>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  if (questions.error) return <ErrorBox error={questions.error} onRetry={questions.reload} />;
  if (!questions.data || current.data === undefined) return <Loading height={420} />;

  const qs = questions.data;
  const profile = current.data.profile;

  if (step === -1 && profile) {
    return <Result profile={profile} onRestart={() => { setAnswers({}); setStep(0); }} onDone={onDone} />;
  }
  if (step >= qs.length) {
    return profile ? <Result profile={profile} onRestart={() => { setAnswers({}); setStep(0); }} onDone={onDone} /> : <Loading />;
  }

  const q = qs[Math.max(step, 0)];
  const valueOf = (i: number) => (q.values ? q.values[i] : i);
  const selected = answers[q.key];
  const selIndex = q.values ? q.values.indexOf(selected as string) : (selected as number | undefined);

  const next = async () => {
    if (selected === undefined) return;
    if (step < qs.length - 1) {
      setStep(step + 1);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await api("/api/profile", { method: "PUT", body: JSON.stringify(answers) });
      invalidate("/api/");
      current.reload();
      setStep(qs.length);
    } catch (e) {
      setError(e as Error);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="card stack" style={{ maxWidth: 720, margin: "0 auto", width: "100%", padding: 32, gap: 22 }}>
      <div className="stack tight">
        <div className="row between small muted strong">
          <span>
            {firstTime ? "Antes de empezar: tu perfil inversor · " : ""}pregunta {step + 1} de {qs.length}
          </span>
          <span>{q.topic}</span>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: `repeat(${qs.length}, 1fr)`, gap: 6 }}>
          {qs.map((_, i) => (
            <div key={i} style={{ height: 6, borderRadius: 99, background: i <= step ? "var(--accent)" : "var(--border)" }} />
          ))}
        </div>
      </div>
      <div>
        <h1 style={{ fontSize: 25, lineHeight: 1.25 }}>{q.question}</h1>
        <p className="muted" style={{ marginTop: 8 }}>{q.hint}</p>
      </div>
      <div className="stack" role="radiogroup" aria-label={q.question} style={{ gap: 10 }}>
        {q.options.map(([label, sub], i) => (
          <button
            key={label}
            type="button"
            role="radio"
            aria-checked={selIndex === i}
            className="option"
            onClick={() => setAnswers({ ...answers, [q.key]: valueOf(i) })}
          >
            <span className="radio" />
            <span className="stack tight" style={{ gap: 2 }}>
              <span className="strong">{label}</span>
              {sub && <span className="muted small">{sub}</span>}
            </span>
          </button>
        ))}
      </div>
      {error && <div className="error-box">{error.message}</div>}
      <div className="row between">
        <button className="btn" onClick={() => setStep(Math.max(step - 1, profile ? -1 : 0))} disabled={step === 0 && !profile}>
          Atrás
        </button>
        <button className="btn primary" onClick={next} disabled={selected === undefined || saving}>
          {step === qs.length - 1 ? (saving ? "Guardando…" : "Ver mi perfil") : "Siguiente"}
        </button>
      </div>
      <p className="muted small" style={{ textAlign: "center" }}>
        Tus respuestas se guardan solo en este ordenador y puedes repetir el test cuando quieras desde «Mi perfil
        inversor».
      </p>
    </div>
  );
}

function Result({ profile, onRestart, onDone }: { profile: Profile; onRestart: () => void; onDone: () => void }) {
  const a = profile.allocation;
  return (
    <div className="card stack" style={{ maxWidth: 720, margin: "0 auto", width: "100%", padding: 32, gap: 20 }}>
      <div className="small strong" style={{ color: "var(--accent-text)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
        Tu perfil inversor
      </div>
      <h1 style={{ fontSize: 34 }}>Perfil {profile.label}</h1>
      <p className="muted" style={{ fontSize: 16, lineHeight: 1.55 }}>{profile.description}</p>
      <div className="grid tiles">
        <div className="card soft stack tight">
          <span className="muted small">Riesgo que toleras</span>
          <strong>Hasta {profile.max_risk_label}</strong>
        </div>
        <div className="card soft stack tight">
          <span className="muted small">Objetivo</span>
          <strong style={{ textTransform: "capitalize" }}>{profile.objective_label}</strong>
        </div>
        <div className="card soft stack tight">
          <span className="muted small">Acciones distintas sugeridas</span>
          <strong>{profile.positions || "Solo ETFs"}</strong>
        </div>
      </div>
      <div className="stack tight">
        <strong>Reparto orientativo de partida</strong>
        <div style={{ display: "flex", height: 18, borderRadius: 99, overflow: "hidden" }} role="img" aria-label={`${a.etf} % ETFs, ${a.stocks} % acciones, ${a.safe} % renta fija o liquidez`}>
          <div style={{ width: `${a.etf}%`, background: "var(--accent)" }} />
          <div style={{ width: `${a.stocks}%`, background: "var(--watch)" }} />
          <div style={{ width: `${a.safe}%`, background: "var(--border)" }} />
        </div>
        <div className="row wrap small muted" style={{ gap: 16 }}>
          <span><strong style={{ color: "var(--text)" }}>{a.etf} %</strong> ETFs indexados</span>
          <span><strong style={{ color: "var(--text)" }}>{a.stocks} %</strong> acciones</span>
          <span><strong style={{ color: "var(--text)" }}>{a.safe} %</strong> renta fija o liquidez</span>
        </div>
      </div>
      {profile.notes.map((n) => (
        <div key={n} className="card soft small">{n}</div>
      ))}
      <div className="card soft small muted">
        Antes de invertir, conviene tener un fondo de emergencia de 3 a 6 meses de gastos. Lo explicaremos en «Cómo invertir».
      </div>
      <div className="row wrap">
        <button className="btn primary" onClick={onDone}>Ver mis recomendaciones →</button>
        <button className="btn" onClick={onRestart}>Repetir el test</button>
      </div>
    </div>
  );
}
