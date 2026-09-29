import { describe, expect, it } from "vitest";
import { parseSSE, toStreamEvent } from "./sse";

describe("parseSSE", () => {
  it("parses complete events and keeps the partial tail", () => {
    const { events, rest } = parseSSE('event: node\ndata: {"node":"a"}\n\nevent: node\ndata: {"no');
    expect(events).toEqual([{ event: "node", data: '{"node":"a"}' }]);
    expect(rest).toBe('event: node\ndata: {"no');
  });

  it("handles CRLF, comments and multi-line data", () => {
    const { events } = parseSSE(": keep-alive\r\n\r\nevent: x\r\ndata: 1\r\ndata: 2\r\n\r\n");
    expect(events).toEqual([{ event: "x", data: "1\n2" }]);
  });

  it("maps payloads to typed events and ignores junk", () => {
    expect(toStreamEvent({ event: "node", data: '{"node":"n","label":"L","status":"ok"}' })).toMatchObject({ event: "node", node: "n", status: "ok" });
    expect(toStreamEvent({ event: "result", data: '{"id":"1"}' })).toMatchObject({ event: "result", assessment: { id: "1" } });
    expect(toStreamEvent({ event: "error", data: '{"code":"x","message":"m","status":500}' })).toMatchObject({ event: "error", code: "x" });
    expect(toStreamEvent({ event: "node", data: "not json" })).toBeNull();
    expect(toStreamEvent({ event: "mystery", data: "{}" })).toBeNull();
  });
});
