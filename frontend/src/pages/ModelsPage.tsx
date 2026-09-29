import { api } from "../api/client";
import type { Metric } from "../api/types";
import { ErrorNotice, Notice, Spinner } from "../components/Notice";
import { humanizeFeature } from "../lib/format";
import { useAsync } from "../lib/useAsync";

const TITLES: Record<string, string> = { fitness_level: "Fitness level model", injury_risk: "Injury risk model" };
const p = (n: number) => `${(n * 100).toFixed(1)}%`;

function MetricRow({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div>
      <dt title={hint}>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

export function ModelsPage() {
  const info = useAsync(() => api.modelInfo(), []);
  const evaluation = useAsync(() => api.modelEvaluation(), []);
  if (info.loading || evaluation.loading) return <Spinner label="Evaluating models on the held-out dataset…" />;
  if (info.error || !info.data) return <ErrorNotice error={info.error} onRetry={info.reload} />;
  const i = info.data;
  const ev = evaluation.data;

  return (
    <div className="stack">
      <div>
        <h1>Model transparency</h1>
        <p className="lead">How the predictions are made, how well they perform on held-out data, and where they fall short.</p>
      </div>

      <Notice tone="warn" title="Read this before trusting a prediction">
        <ul className="bullets">
          {i.limitations.map((l, k) => (
            <li key={k}>{l}</li>
          ))}
        </ul>
      </Notice>

      {evaluation.error != null && <ErrorNotice error={evaluation.error} onRetry={evaluation.reload} />}

      {Object.entries(i.models).map(([key, m]) => {
        const metric: Metric | undefined = ev?.models[key] ?? m.training_evaluation;
        const importance = Object.entries(m.global_feature_importance).sort((a, b) => b[1] - a[1]);
        const maxImp = Math.max(...importance.map(([, v]) => v), 0.0001);
        return (
          <section className="card" key={key} aria-labelledby={`m-${key}`}>
            <h2 id={`m-${key}`}>{TITLES[key] ?? key}</h2>
            <p className="muted small">
              Classes: {m.classes.join(" → ")} · {ev?.source === "live" ? "evaluated just now" : "stored evaluation"} on {metric?.samples.toLocaleString()} held-out rows
            </p>
            {metric && (
              <dl className="facts">
                <MetricRow label="Accuracy" value={p(metric.accuracy)} hint="Share of held-out rows classified exactly right" />
                <MetricRow label="Within one class" value={p(metric.within_one_class_accuracy)} hint="Prediction is the true class or an adjacent one" />
                <MetricRow label="Macro F1" value={metric.macro_f1.toFixed(3)} hint="Average F1 across classes, so rare classes count equally" />
                <MetricRow label="Calibration error" value={metric.expected_calibration_error.toFixed(3)} hint="How far stated confidence is from actual accuracy (lower is better)" />
                <MetricRow label="Cross-validated accuracy" value={`${p(m.cross_validation.accuracy_mean)} ± ${p(m.cross_validation.accuracy_std)}`} hint={`${m.cross_validation.folds}-fold CV on training data`} />
              </dl>
            )}
            {metric && (
              <>
                <h3>Precision per class</h3>
                <ul className="ladder">
                  {Object.entries(metric.precision_per_class).map(([c, v]) => (
                    <li key={c}>
                      <span className="ladder-name">{c}</span>
                      <span className="bar">
                        <span className="bar-fill" style={{ width: `${v * 100}%` }} />
                      </span>
                      <span className="ladder-pct">{p(v)}</span>
                    </li>
                  ))}
                </ul>
              </>
            )}
            <h3>What the model relies on</h3>
            <ul className="ladder">
              {importance.map(([f, v]) => (
                <li key={f}>
                  <span className="ladder-name">{humanizeFeature(f)}</span>
                  <span className="bar">
                    <span className="bar-fill" style={{ width: `${(v / maxImp) * 100}%` }} />
                  </span>
                  <span className="ladder-pct">{(v * 100).toFixed(0)}%</span>
                </li>
              ))}
            </ul>
            <p className="hint">{m.data.provenance}</p>
          </section>
        );
      })}

      <section className="card">
        <h2>Guardrails</h2>
        <ul className="bullets">
          {i.guardrails.map((g, k) => (
            <li key={k}>{g}</li>
          ))}
        </ul>
        <p className="muted small">
          Trained {new Date(i.trained_at).toLocaleDateString()} · scikit-learn {i.environment.scikit_learn} · Python {i.environment.python}
        </p>
      </section>
    </div>
  );
}
