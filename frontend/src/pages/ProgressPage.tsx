import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { WEEKDAYS, type ProgressLogIn } from "../api/types";
import { BarChart, LineChart } from "../components/Viz";
import { Badge, ErrorNotice, Notice, Spinner } from "../components/Notice";
import { pct, today } from "../lib/format";
import { useAsync } from "../lib/useAsync";

export function ProgressPage() {
  const { id = "" } = useParams();
  const plan = useAsync(() => api.getAssessment(id), [id]);
  const summary = useAsync(() => api.progress(id), [id]);
  const logs = useAsync(() => api.listLogs(id), [id]);
  const [error, setError] = useState<unknown>(null);
  const [kind, setKind] = useState<"session" | "weight">("session");
  const [form, setForm] = useState({ logged_on: today(), planned_day: "", completed: true, duration: "", rpe: "", weight: "", notes: "" });

  const refresh = () => {
    summary.reload();
    logs.reload();
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const body: ProgressLogIn =
      kind === "session"
        ? {
            kind,
            logged_on: form.logged_on,
            completed: form.completed,
            planned_day: form.planned_day || null,
            duration_minutes: form.duration ? Number(form.duration) : null,
            rpe: form.rpe ? Number(form.rpe) : null,
            notes: form.notes || null,
          }
        : { kind, completed: true, logged_on: form.logged_on, weight_kg: Number(form.weight), notes: form.notes || null };
    try {
      await api.addLog(id, body);
      setForm((f) => ({ ...f, duration: "", rpe: "", weight: "", notes: "" }));
      refresh();
    } catch (err) {
      setError(err);
    }
  };

  if (summary.loading || plan.loading) return <Spinner label="Loading progress…" />;
  if (summary.error || plan.error || !summary.data) return <ErrorNotice error={summary.error ?? plan.error} onRetry={() => { summary.reload(); plan.reload(); }} />;
  const s = summary.data;
  const days = plan.data?.workout?.weekly_schedule.map((d) => d.day) ?? [...WEEKDAYS];

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Progress</h1>
          <p className="muted">
            <Link to={`/plans/${id}`}>← Back to plan</Link> · week {s.weeks_on_plan} on this plan
          </p>
        </div>
      </div>

      {s.deload_due && (
        <Notice tone="warn" title="A lighter week is due">
          You've been at it for a while or your sessions have felt very hard. Re-plan to get a deload week built in.
        </Notice>
      )}

      <section className="card">
        <dl className="facts">
          <div>
            <dt>Adherence (last 4 weeks)</dt>
            <dd className="big">{pct(s.adherence_pct)}</dd>
          </div>
          <div>
            <dt>Sessions (28 days)</dt>
            <dd>
              {s.sessions_last_28_days} <span className="muted">/ {s.planned_sessions_per_week} per week planned</span>
            </dd>
          </div>
          <div>
            <dt>Average effort (RPE)</dt>
            <dd>{s.average_rpe ?? "—"}</dd>
          </div>
          <div>
            <dt>Weight change</dt>
            <dd>{s.weight_change_kg == null ? "—" : `${s.weight_change_kg > 0 ? "+" : ""}${s.weight_change_kg.toFixed(1)} kg`}</dd>
          </div>
        </dl>
        {s.notes.length > 0 && (
          <ul className="bullets">
            {s.notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        )}
      </section>

      <div className="grid grid-2">
        <section className="card">
          <h3>Sessions per week</h3>
          <BarChart label="Completed sessions per week against plan" data={s.weekly.map((w) => ({ label: w.week_start.slice(5), value: w.sessions, target: w.planned }))} />
          <p className="hint">The line marks the number of sessions planned.</p>
        </section>
        <section className="card">
          <h3>Body weight</h3>
          <LineChart label="Body weight over time" points={s.weights} />
        </section>
      </div>

      <section className="card">
        <h3>Log an entry</h3>
        {error != null && <ErrorNotice error={error} />}
        <div className="tabs" role="tablist" aria-label="Entry type">
          {(["session", "weight"] as const).map((k) => (
            <button key={k} type="button" role="tab" aria-selected={kind === k} className={kind === k ? "tab tab-on" : "tab"} onClick={() => setKind(k)}>
              {k === "session" ? "Workout" : "Weigh-in"}
            </button>
          ))}
        </div>
        <form className="form" onSubmit={submit}>
          <div className="grid grid-3">
            <div className="field">
              <label htmlFor="logged_on">Date</label>
              <input id="logged_on" type="date" max={today()} value={form.logged_on} onChange={(e) => setForm({ ...form, logged_on: e.target.value })} required />
            </div>
            {kind === "session" ? (
              <>
                <div className="field">
                  <label htmlFor="planned_day">Planned day</label>
                  <select id="planned_day" value={form.planned_day} onChange={(e) => setForm({ ...form, planned_day: e.target.value })}>
                    <option value="">Unplanned</option>
                    {days.map((d) => (
                      <option key={d}>{d}</option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="duration">Minutes</label>
                  <input id="duration" inputMode="numeric" value={form.duration} onChange={(e) => setForm({ ...form, duration: e.target.value })} />
                </div>
                <div className="field">
                  <label htmlFor="rpe">Effort (1–10)</label>
                  <input id="rpe" inputMode="numeric" value={form.rpe} onChange={(e) => setForm({ ...form, rpe: e.target.value })} />
                </div>
                <label className="check">
                  <input type="checkbox" checked={form.completed} onChange={(e) => setForm({ ...form, completed: e.target.checked })} />
                  <span>Completed</span>
                </label>
              </>
            ) : (
              <div className="field">
                <label htmlFor="weight">Weight (kg)</label>
                <input id="weight" inputMode="decimal" value={form.weight} onChange={(e) => setForm({ ...form, weight: e.target.value })} required />
              </div>
            )}
          </div>
          <div className="field">
            <label htmlFor="notes">Notes (optional)</label>
            <input id="notes" maxLength={300} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          </div>
          <button className="btn btn-primary" type="submit">
            Save entry
          </button>
        </form>
      </section>

      <section className="card">
        <h3>History</h3>
        {(logs.data ?? []).length === 0 ? (
          <p className="muted">Nothing logged yet.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Date</th>
                <th scope="col">Entry</th>
                <th scope="col">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {(logs.data ?? []).map((l) => (
                <tr key={l.id}>
                  <td>{l.logged_on}</td>
                  <td>
                    {l.kind === "weight" ? (
                      <>Weigh-in: {l.weight_kg} kg</>
                    ) : (
                      <>
                        {l.completed ? <Badge tone="good">Done</Badge> : <Badge tone="warn">Skipped</Badge>} {l.planned_day ?? "Unplanned"}
                        {l.duration_minutes ? ` · ${l.duration_minutes} min` : ""}
                        {l.rpe ? ` · RPE ${l.rpe}` : ""}
                      </>
                    )}
                    {l.notes && <div className="muted small">{l.notes}</div>}
                  </td>
                  <td>
                    <button className="btn btn-small" aria-label={`Delete entry from ${l.logged_on}`} onClick={() => api.deleteLog(id, l.id).then(refresh, setError)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
