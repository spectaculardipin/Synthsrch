/** Citation tokenizer: splits "[S1]" markers into renderable parts. */
export type CitePart = { text: string } | { cite: number };

export function splitCitations(text: string): CitePart[] {
  const parts: CitePart[] = [];
  const re = /\[S(\d+)\]/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push({ text: text.slice(last, m.index) });
    parts.push({ cite: Number(m[1]) });
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push({ text: text.slice(last) });
  return parts;
}
