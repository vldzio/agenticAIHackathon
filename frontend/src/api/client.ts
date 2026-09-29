import { parseSSE, toStreamEvent } from "./sse";
import type {
  Assessment,
  AssessmentSummary,
  Health,
  Mode,
  ModelEvaluation,
  ModelInfo,
  ProfileIn,
  ProgressLogIn,
  ProgressLogOut,
  ProgressSummary,
  StreamEvent,
  WorkflowNode,
} from "./types";
import { getApiKey, getDeviceId } from "../lib/storage";

export const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "/api/v1";

export interface FieldError {
  field: string;
  message: string;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly fieldErrors: FieldError[] = [],
    public readonly requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function headers(mode: Mode | null, json = false): Headers {
  const h = new Headers({ "X-Device-Id": getDeviceId() });
  if (json) h.set("Content-Type", "application/json");
  if (mode === "live") {
    const key = getApiKey();
    if (key) h.set("X-Gemini-Api-Key", key); // BYOK: per-request only, never persisted server-side
  }
  return h;
}

async function toApiError(res: Response): Promise<ApiError> {
  try {
    const body = await res.json();
    const err = body?.error;
    if (err) return new ApiError(res.status, err.code ?? "error", err.message ?? res.statusText, err.field_errors ?? [], err.request_id);
  } catch {
    /* non-JSON body */
  }
  const fallback: Record<number, string> = {
    413: "That request was too large.",
    429: "Too many requests — please wait a moment and try again.",
    502: "The service is temporarily unavailable.",
    503: "The service is temporarily unavailable.",
  };
  return new ApiError(res.status, "http_error", fallback[res.status] ?? `Request failed (${res.status}).`);
}

async function request<T>(path: string, init: Omit<RequestInit, "mode"> & { llmMode?: Mode | null } = {}): Promise<T> {
  const { llmMode = null, ...rest } = init;
  const hasBody = rest.body !== undefined;
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...rest, headers: headers(llmMode, hasBody) });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new ApiError(0, "network_error", "Cannot reach the AetherFit server. Check your connection and try again.");
  }
  if (!res.ok) throw await toApiError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

const json = (body: unknown): { body: string } => ({ body: JSON.stringify(body) });

export const api = {
  health: () => request<Health>("/health"),
  workflow: () => request<{ nodes: WorkflowNode[] }>("/workflow"),
  modelInfo: () => request<ModelInfo>("/models/info"),
  modelEvaluation: (refresh = false) => request<ModelEvaluation>(`/models/evaluation${refresh ? "?refresh=true" : ""}`),

  listAssessments: () => request<AssessmentSummary[]>("/assessments"),
  getAssessment: (id: string) => request<Assessment>(`/assessments/${id}`),
  deleteAssessment: (id: string) => request<void>(`/assessments/${id}`, { method: "DELETE" }),
  createAssessment: (profile: ProfileIn, mode: Mode) =>
    request<Assessment>("/assessments", { method: "POST", llmMode: mode, ...json({ mode, profile }) }),
  replan: (id: string, mode: Mode) => request<Assessment>(`/assessments/${id}/replan`, { method: "POST", llmMode: mode, ...json({ mode }) }),

  progress: (id: string) => request<ProgressSummary>(`/assessments/${id}/progress`),
  listLogs: (id: string) => request<ProgressLogOut[]>(`/assessments/${id}/logs`),
  addLog: (id: string, log: ProgressLogIn) => request<ProgressLogOut>(`/assessments/${id}/logs`, { method: "POST", ...json(log) }),
  deleteLog: (id: string, logId: number) => request<void>(`/assessments/${id}/logs/${logId}`, { method: "DELETE" }),
};

/**
 * POST to an SSE endpoint with fetch (EventSource cannot send headers or a body) and call `onEvent`
 * for every server event. Resolves with the final assessment, or rejects with an ApiError.
 */
export async function streamAssessment(
  path: "/assessments/stream" | `/assessments/${string}/replan/stream`,
  body: unknown,
  mode: Mode,
  onEvent: (e: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<Assessment> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { method: "POST", headers: headers(mode, true), body: JSON.stringify(body), signal });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new ApiError(0, "network_error", "Cannot reach the AetherFit server. Check your connection and try again.");
  }
  if (!res.ok) throw await toApiError(res);
  if (!res.body) throw new ApiError(0, "stream_unsupported", "Your browser does not support streaming responses.");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: Assessment | null = null;

  const handle = (text: string) => {
    const parsed = parseSSE(text);
    buffer = parsed.rest;
    for (const raw of parsed.events) {
      const event = toStreamEvent(raw);
      if (!event) continue;
      if (event.event === "error") throw new ApiError(event.status, event.code, event.message);
      if (event.event === "result") result = event.assessment;
      onEvent(event);
    }
  };

  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    handle(buffer + decoder.decode(value, { stream: true }));
  }
  handle(buffer + decoder.decode() + "\n\n");
  if (!result) throw new ApiError(502, "stream_ended", "The connection closed before the plan was finished. Please try again.");
  return result;
}

export const streamCreate = (profile: ProfileIn, mode: Mode, onEvent: (e: StreamEvent) => void, signal?: AbortSignal) =>
  streamAssessment("/assessments/stream", { mode, profile }, mode, onEvent, signal);

export const streamReplan = (id: string, mode: Mode, onEvent: (e: StreamEvent) => void, signal?: AbortSignal) =>
  streamAssessment(`/assessments/${id}/replan/stream`, { mode }, mode, onEvent, signal);

/** Exports need the device header, so fetch as a blob and trigger the download ourselves. */
export async function downloadExport(id: string, fmt: "pdf" | "ics" | "json"): Promise<void> {
  const res = await fetch(`${API_BASE}/assessments/${id}/export.${fmt}`, { headers: headers(null) });
  if (!res.ok) throw await toApiError(res);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `aetherfit-${id.slice(0, 8)}.${fmt}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Human-friendly message + hint for an error, used by the UI. */
export function describeError(e: unknown): { title: string; detail: string } {
  if (e instanceof ApiError) {
    switch (e.code) {
      case "llm_auth":
        return { title: "Gemini rejected your API key", detail: "Check the key in Settings, or switch to Simulated mode." };
      case "llm_rate_limited":
        return { title: "Gemini quota reached", detail: "Your Gemini key is rate-limited. Wait a minute and retry, or use Simulated mode." };
      case "live_key_required":
        return { title: "API key needed for Live mode", detail: "Add your Gemini API key in Settings, or switch to Simulated mode." };
      case "invalid_api_key_format":
        return { title: "That API key looks invalid", detail: "Gemini keys are 30+ characters of letters, digits, '-' and '_'." };
      case "network_error":
        return { title: "Can't reach the server", detail: e.message };
      case "ml_failure":
        return { title: "The prediction models are unavailable", detail: "This is a server problem, not your input. Try again shortly." };
      default:
        return { title: e.status >= 500 ? "Something went wrong on our side" : "Request failed", detail: e.message };
    }
  }
  return { title: "Unexpected error", detail: e instanceof Error ? e.message : String(e) };
}
