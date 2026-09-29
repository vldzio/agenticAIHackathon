import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, describeError, streamCreate } from "./client";
import { setApiKey } from "../lib/storage";
import { makeAssessment } from "../test/fixtures";
import type { ProfileIn, StreamEvent } from "./types";

const KEY = "AIzaSyExampleExampleExample12345";
const profile = makeAssessment().profile as ProfileIn;

function sseResponse(chunks: string[], status = 200): Response {
  const enc = new TextEncoder();
  const body = new ReadableStream({
    start(c) {
      chunks.forEach((x) => c.enqueue(enc.encode(x)));
      c.close();
    },
  });
  return new Response(body, { status, headers: { "Content-Type": "text/event-stream" } });
}

const frame = (event: string, data: unknown) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;

describe("api client", () => {
  const fetchMock = vi.fn();
  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });
  afterEach(() => vi.unstubAllGlobals());

  const sentHeaders = () => fetchMock.mock.calls[0]![1].headers as Headers;

  it("always sends the device id and never the key in simulated mode", async () => {
    setApiKey(KEY);
    fetchMock.mockResolvedValue(new Response("[]", { status: 200 }));
    await api.listAssessments();
    expect(sentHeaders().get("X-Device-Id")).toMatch(/^[A-Za-z0-9_-]{8,64}$/);
    expect(sentHeaders().get("X-Gemini-Api-Key")).toBeNull();

    fetchMock.mockClear();
    fetchMock.mockResolvedValue(new Response(JSON.stringify(makeAssessment()), { status: 201 }));
    await api.createAssessment(profile, "mock");
    expect(sentHeaders().get("X-Gemini-Api-Key")).toBeNull();
  });

  it("sends the key as a header (not in the body or URL) in live mode", async () => {
    setApiKey(KEY);
    fetchMock.mockResolvedValue(new Response(JSON.stringify(makeAssessment()), { status: 201 }));
    await api.createAssessment(profile, "live");
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(sentHeaders().get("X-Gemini-Api-Key")).toBe(KEY);
    expect(String(url)).not.toContain(KEY);
    expect(String(init.body)).not.toContain(KEY);
  });

  it("turns error responses into ApiError with field errors", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ error: { code: "validation_error", message: "Invalid", field_errors: [{ field: "profile.age", message: "too low" }], request_id: "r1" } }), { status: 422 }),
    );
    const err = await api.getAssessment("x").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ status: 422, code: "validation_error", requestId: "r1", fieldErrors: [{ field: "profile.age", message: "too low" }] });
  });

  it("reports network failures clearly", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));
    const err = await api.health().catch((e) => e);
    expect(err).toMatchObject({ code: "network_error", status: 0 });
    expect(describeError(err).title).toMatch(/reach/i);
  });

  it("returns undefined for 204", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
    await expect(api.deleteAssessment("x")).resolves.toBeUndefined();
  });

  it("streams node events then resolves with the assessment", async () => {
    const a = makeAssessment();
    const whole = frame("start", { nodes: [{ name: "n1", label: "One", section: "profile" }] }) + frame("node", { node: "n1", label: "One", status: "ok" }) + frame("result", a);
    const mid = Math.floor(whole.length / 2); // split mid-frame to exercise buffering
    fetchMock.mockResolvedValue(sseResponse([whole.slice(0, mid), whole.slice(mid)]));
    const seen: StreamEvent[] = [];
    const result = await streamCreate(profile, "mock", (e) => seen.push(e));
    expect(result.id).toBe(a.id);
    expect(seen.map((e) => e.event)).toEqual(["start", "node", "result"]);
  });

  it("rejects when the stream reports an error event", async () => {
    fetchMock.mockResolvedValue(sseResponse([frame("error", { code: "llm_rate_limited", message: "quota", status: 429 })]));
    const err = await streamCreate(profile, "live", () => {}).catch((e) => e);
    expect(err).toMatchObject({ code: "llm_rate_limited", status: 429 });
    expect(describeError(err).title).toMatch(/quota/i);
  });

  it("rejects when the stream ends without a result", async () => {
    fetchMock.mockResolvedValue(sseResponse([frame("start", { nodes: [] })]));
    await expect(streamCreate(profile, "mock", () => {})).rejects.toMatchObject({ code: "stream_ended" });
  });

  it("surfaces HTTP errors returned before streaming starts", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ error: { code: "llm_auth", message: "bad key" } }), { status: 401 }));
    await expect(streamCreate(profile, "live", () => {})).rejects.toMatchObject({ status: 401, code: "llm_auth" });
  });
});
