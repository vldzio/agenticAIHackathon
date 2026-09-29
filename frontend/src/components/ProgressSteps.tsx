import type { SectionStatus, WorkflowNode } from "../api/types";

export type StepState = Record<string, SectionStatus | "running" | undefined>;

const ICON: Record<string, string> = { ok: "✓", partial: "!", failed: "✕", skipped: "–", running: "…" };
const TEXT: Record<string, string> = { ok: "done", partial: "partly done", failed: "failed", skipped: "skipped", running: "in progress" };

/** Live checklist of the agent workflow, driven by SSE `node` events. */
export function ProgressSteps({ nodes, state }: { nodes: WorkflowNode[]; state: StepState }) {
  const firstPending = nodes.find((n) => !state[n.name])?.name;
  return (
    <ol className="steps" aria-label="Plan generation progress" aria-live="polite">
      {nodes.map((n) => {
        const s = state[n.name] ?? (n.name === firstPending ? "running" : undefined);
        return (
          <li key={n.name} className={`step step-${s ?? "pending"}`}>
            <span className="step-icon" aria-hidden="true">
              {s ? ICON[s] : "·"}
            </span>
            <span className="step-label">{n.label}</span>
            {s && <span className="step-state">{TEXT[s]}</span>}
          </li>
        );
      })}
    </ol>
  );
}

export const DEFAULT_NODES: WorkflowNode[] = [
  { name: "form_parser", label: "Validating your profile", section: "profile" },
  { name: "input_normalizer", label: "Interpreting your answers", section: "normalization" },
  { name: "fitness_scorer", label: "Estimating fitness level", section: "fitness" },
  { name: "injury_assessor", label: "Estimating injury risk", section: "injury" },
  { name: "safety_guardrail", label: "Applying safety rules", section: "safety" },
  { name: "workout_planner", label: "Building your workout plan", section: "workout" },
  { name: "nutrition_advisor", label: "Building your nutrition plan", section: "nutrition" },
  { name: "recovery_optimizer", label: "Planning recovery", section: "recovery" },
];
