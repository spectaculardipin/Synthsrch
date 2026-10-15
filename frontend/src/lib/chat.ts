/** Citation tokenizer: splits "[S1]" and multi markers like "[S1, S3]"
 *  into renderable parts. Multi-cites become separate badges so each stays
 *  small and inline — never a block that breaks paragraph flow. */
export type CitePart = { text: string } | { cite: number };

export function splitCitations(text: string): CitePart[] {
  const parts: CitePart[] = [];
  const re = /\[S?(\d+(?:\s*,?\s*S?\d+)*)\]/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    // Only treat as citation when the bracket starts with S (e.g. [S1] / [S1, S3]).
    if (m[0][1] !== "S" && m[0][1] !== "s") continue;
    if (m.index > last) parts.push({ text: text.slice(last, m.index) });
    const nums = m[1].match(/\d+/g) ?? [];
    nums.forEach((n, i) => {
      if (i > 0) parts.push({ text: ", " });
      parts.push({ cite: Number(n) });
    });
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push({ text: text.slice(last) });
  return parts;
}

/** Allowlist for rendering provider-supplied URLs as links: http(s) only.
 *  Anything else (javascript:, data:, file:, …) renders as plain text. */
export function safeUrl(url: string): string | null {
  try {
    const u = new URL(url);
    return u.protocol === "http:" || u.protocol === "https:" ? url : null;
  } catch {
    return null;
  }
}
