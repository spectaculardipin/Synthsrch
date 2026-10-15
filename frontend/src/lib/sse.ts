/** Buffered SSE parser: reassembles `data:` payloads split across chunks.
 *
 *  The old reader split each decoded chunk on "\n" with no carry-over, so a
 *  JSON payload straddling two TCP chunks failed to parse and was silently
 *  dropped — the stream looked "paused" mid-response. This buffer keeps the
 *  incomplete tail until its terminating blank line arrives.
 */
export class SseBuffer {
  private tail = "";

  /** Feed decoded text; returns complete payloads (without the `data:` prefix). */
  push(text: string): string[] {
    this.tail += text;
    const out: string[] = [];
    for (;;) {
      const end = this.tail.indexOf("\n\n");
      if (end === -1) break;
      const block = this.tail.slice(0, end);
      this.tail = this.tail.slice(end + 2);
      for (const line of block.split("\n")) {
        if (line.startsWith("data: ")) out.push(line.slice(6).trim());
      }
    }
    return out;
  }
}
