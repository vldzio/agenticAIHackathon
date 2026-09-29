import { Link } from "react-router-dom";
import { api } from "../api/client";
import { Badge, ErrorNotice, Notice, Spinner } from "../components/Notice";
import { formatDateTime } from "../lib/format";
import { useAsync } from "../lib/useAsync";

export function PlansPage() {
  const { data, error, loading, reload } = useAsync(() => api.listAssessments(), []);
  if (loading) return <Spinner label="Loading your plans…" />;
  if (error) return <ErrorNotice error={error} onRetry={reload} />;
  const plans = data ?? [];
  return (
    <div className="stack">
      <div className="page-head">
        <h1>My plans</h1>
        <Link className="btn btn-primary" to="/">
          New plan
        </Link>
      </div>
      {plans.length === 0 ? (
        <Notice tone="info" title="No saved plans yet">
          Plans you create on this device appear here. <Link to="/">Create your first plan</Link>.
        </Notice>
      ) : (
        <ul className="cards">
          {plans.map((p) => (
            <li key={p.id} className="card">
              <Link to={`/plans/${p.id}`} className="card-link">
                <strong>{p.user_name ? `${p.user_name} · ` : ""}{p.fitness_goal}</strong>
                <span className="muted small">{formatDateTime(p.created_at)}</span>
              </Link>
              <div className="chips">
                {p.fitness_level && <Badge>{p.fitness_level}</Badge>}
                {p.injury_risk && <Badge tone={p.injury_risk.startsWith("Low") ? "good" : p.injury_risk.startsWith("Moderate") ? "warn" : "bad"}>{p.injury_risk}</Badge>}
                {p.safety_level && p.safety_level !== "standard" && <Badge tone="warn">{p.safety_level.replace("_", " ")}</Badge>}
                {p.status !== "complete" && <Badge tone="warn">{p.status}</Badge>}
                <Badge tone={p.simulated ? "sim" : "good"}>{p.simulated ? "Simulated" : "Gemini"}</Badge>
              </div>
              <p className="small muted">
                {p.sessions_per_week ?? "—"} sessions/week · {p.daily_calorie_target ?? "—"} kcal
                {p.parent_id && " · re-plan"}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
