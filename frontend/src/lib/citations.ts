export type Segment = { type: "text"; text: string } | { type: "cite"; n: number };

/**
 * Split an answer into plain text and citation markers so the UI can render
 * "[1]" as a clickable chip. Numbers that don't match a real source stay as text.
 *   "Cats purr [1][3]." -> text "Cats purr ", cite 1, cite 3, text "."
 */
export function parseAnswer(answer: string, validNumbers: Set<number>): Segment[] {
  const segments: Segment[] = [];
  const re = /\[(\d+)\]/g;
  let last = 0;
  let match: RegExpExecArray | null;
  while ((match = re.exec(answer)) !== null) {
    const n = Number(match[1]);
    if (!validNumbers.has(n)) continue;
    if (match.index > last) segments.push({ type: "text", text: answer.slice(last, match.index) });
    segments.push({ type: "cite", n });
    last = match.index + match[0].length;
  }
  if (last < answer.length) segments.push({ type: "text", text: answer.slice(last) });
  return mergeText(segments);
}

function mergeText(segments: Segment[]): Segment[] {
  const out: Segment[] = [];
  for (const s of segments) {
    const prev = out[out.length - 1];
    if (s.type === "text" && prev?.type === "text") prev.text += s.text;
    else out.push(s.type === "text" ? { ...s } : s);
  }
  return out;
}

/** Plain-text version for the Copy button: "[1]" stays, but invalid markers are removed. */
export function answerForClipboard(answer: string, validNumbers: Set<number>): string {
  return answer.replace(/\[(\d+)\]/g, (m, d) => (validNumbers.has(Number(d)) ? m : "")).trim();
}
