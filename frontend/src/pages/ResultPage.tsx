import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, downloadExport, streamReplan } from "../api/client";
import type { Assessment } from "../api/types";
import { Badge, ErrorNotice, Notice, Spinner } from "../components/Notice";
import { Nutrition, Overview, Recovery, SafetyBanner, Workout } from "../components/PlanSections";
import { ProgressSteps } from "../components/ProgressSteps";
import { formatDateTime } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import { useGeneration } from "../lib/useGeneration";
import { useSettings } from "../state/settings";

const TABS = ["Overview", "Workout", "Nutrition", "Recovery"] as const;
type Tab = (typeof TABS)[number];

const SECTION_LABEL: Record<string, string> = {
  profile: "profile",
  normalization: "input interpretation",
  fitness: "fitness level",
  injury: "injury risk",
  safety: "safety rules",
  workout: "workout plan",
  nutrition: "nutrition plan",
  recovery: "recovery plan",
};

export function PlanView({ a }: { a: Assessment }) {
  const [tab, setTab] = useState<Tab>("Overview");
  const failed = Object.entries(a.sections ?? {}).filter(([, s]) => s === "failed" || s === "partial" || s === "skipped");
  return (
    <div className="stack">
      {a.simulated && (
        <Notice tone="info" title="Simulated plan">
          The workout, nutrition and recovery text was produced by built-in rules, not an AI model. Fitness and injury predictions are from the trained models.
        </Notice>
      )}
      <SafetyBanner a={a} />
      {a.status !== "complete" && (
        <Notice tone="warn" title="Some parts of this plan are missing">
          <ul className="bullets">
            {failed.map(([k, s]) => (
              <li key={k}>
                {SECTION_LABEL[k] ?? k}: {s}
              </li>
            ))}
            {(a.errors ?? []).map((e, i) => (
              <li key={i}>{e.message}</li>
            ))}
          </ul>
        </Notice>
      )}
      {(a.warnings ?? []).length > 0 && (
        <Notice tone="info" title="Notes on this plan">
          <ul className="bullets">
            {(a.warnings ?? []).map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </Notice>
      )}

      <div className="tabs" role="tablist" aria-label="Plan sections">
        {TABS.map((t) => (
          <button key={t} role="tab" id={`tab-${t}`} aria-selected={tab === t} aria-controls={`panel-${t}`} className={tab === t ? "tab tab-on" : "tab"} onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
        {tab === "Overview" && <Overview a={a} />}
        {tab === "Workout" && <Workout a={a} />}
        {tab === "Nutrition" && <Nutrition a={a} />}
        {tab === "Recovery" && <Recovery a={a} />}
      </div>
      <p className="disclaimer">{a.safety?.disclaimer ?? "AetherFit is an educational tool, not medical advice."}</p>
    </div>
  );
}

export function ResultPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const { mode, liveReady } = useSettings();
  const { data, error, loading, reload } = useAsync(() => api.getAssessment(id), [id]);
  const gen = useGeneration();
  const [actionError, setActionError] = useState<unknown>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const guard = async (name: string, fn: () => Promise<unknown>) => {
    setBusy(name);
    setActionError(null);
    try {
      await fn();
    } catch (e) {
      setActionError(e);
    } finally {
      setBusy(null);
    }
  };

  if (loading) return <Spinner label="Loading your plan…" />;
  if (error || !data) return <ErrorNotice error={error} onRetry={reload} />;
  const a = data;

  const replan = async () => {
    const result = await gen.run((onEvent, signal) => streamReplan(a.id, mode, onEvent, signal));
    if (result) navigate(`/plans/${result.id}`);
  };
  const liveBlocked = mode === "live" && !liveReady;

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>{a.profile.user_name ? `${a.profile.user_name}'s plan` : "Your plan"}</h1>
          <p className="muted">
            {formatDateTime(a.created_at)} · {a.profile.fitness_goal} · <Badge tone={a.simulated ? "sim" : "good"}>{a.simulated ? "Simulated" : "Gemini"}</Badge>{" "}
            {a.parent_id && <Link to={`/plans/${a.parent_id}`}>Re-plan of an earlier plan</Link>}
          </p>
        </div>
        <div className="actions">
          <button className="btn" disabled={busy !== null} onClick={() => guard("pdf", () => downloadExport(a.id, "pdf"))}>
            PDF
          </button>
          <button className="btn" disabled={busy !== null || !a.workout} onClick={() => guard("ics", () => downloadExport(a.id, "ics"))} title="Add your workouts to a calendar app">
            Calendar (.ics)
          </button>
          <button className="btn" disabled={busy !== null} onClick={() => guard("json", () => downloadExport(a.id, "json"))}>
            JSON
          </button>
          <Link className="btn" to={`/plans/${a.id}/progress`}>
            Track progress
          </Link>
          <button className="btn btn-primary" disabled={gen.running || liveBlocked} onClick={replan} title={liveBlocked ? "Add your Gemini key in Settings first" : "Regenerate using your logged progress"}>
            Re-plan
          </button>
        </div>
      </div>

      {actionError != null && <ErrorNotice error={actionError} />}
      {gen.error != null && <ErrorNotice error={gen.error} onRetry={replan} />}
      {gen.running && (
        <section className="card" aria-busy="true">
          <h2>Re-planning from your progress…</h2>
          <ProgressSteps nodes={gen.nodes} state={gen.steps} />
        </section>
      )}
      {a.progress_context && (
        <Notice tone="info" title="Adjusted using your progress">
          <ul className="bullets">
            {a.progress_context.notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </Notice>
      )}

      <PlanView a={a} />

      <div className="row end">
        <button
          className="btn btn-danger"
          disabled={busy !== null}
          onClick={() => {
            if (confirm("Delete this plan and its progress logs? This cannot be undone.")) guard("delete", async () => {
              await api.deleteAssessment(a.id);
              navigate("/plans");
            });
          }}
        >
          Delete plan
        </button>
      </div>
    </div>
  );
}
