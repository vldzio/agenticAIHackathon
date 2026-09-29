import type { StreamEvent } from "./types";

export interface RawEvent {
  event: string;
  data: string;
}

/**
 * Incremental Server-Sent-Events parser. Feed it text chunks as they arrive; it returns every complete
 * event and keeps the trailing partial frame in `rest` for the next call.
 */
export function parseSSE(buffer: string): { events: RawEvent[]; rest: string } {
  const normalised = buffer.replace(/\r\n/g, "\n");
  const frames = normalised.split("\n\n");
  const rest = frames.pop() ?? "";
  const events: RawEvent[] = [];
  for (const frame of frames) {
    let event = "message";
    const data: string[] = [];
    for (const line of frame.split("\n")) {
      if (line.startsWith(":")) continue; // comment / keep-alive
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
    }
    if (data.length) events.push({ event, data: data.join("\n") });
  }
  return { events, rest };
}

export function toStreamEvent(raw: RawEvent): StreamEvent | null {
  let payload: unknown;
  try {
    payload = JSON.parse(raw.data);
  } catch {
    return null;
  }
  switch (raw.event) {
    case "start":
    case "node":
    case "error":
      return { ...(payload as object), event: raw.event } as StreamEvent;
    case "result":
      return { event: "result", assessment: payload as never };
    default:
      return null;
  }
}
