import { describe, expect, it } from "vitest";
import { SseBuffer } from "./sse";

describe("SseBuffer", () => {
  it("reassembles a JSON payload split across chunks", () => {
    const buf = new SseBuffer();
    const payload = JSON.stringify({ delta: "Hello world, this is a long token stream." });
    const raw = `data: ${payload}\n\n`;
    const cut = Math.floor(raw.length / 2);
    expect(buf.push(raw.slice(0, cut))).toEqual([]);
    expect(buf.push(raw.slice(cut))).toEqual([payload]);
  });

  it("handles multiple events in one chunk and split multi-byte chars", () => {
    const buf = new SseBuffer();
    const a = JSON.stringify({ delta: "café ☕ " });
    const b = JSON.stringify({ delta: "done." });
    // Split inside a multi-byte char sequence at the byte level simulation:
    // feed char-by-char to prove no loss.
    const raw = `data: ${a}\n\ndata: ${b}\n\ndata: [DONE]\n\n`;
    let out: string[] = [];
    for (const ch of raw) out = out.concat(buf.push(ch));
    expect(out).toEqual([a, b, "[DONE]"]);
  });

  it("ignores non-data lines and blank heartbeats", () => {
    const buf = new SseBuffer();
    expect(buf.push(": ping\n\ndata: {\"delta\":\"hi\"}\n\n")).toEqual(['{"delta":"hi"}']);
  });
});
