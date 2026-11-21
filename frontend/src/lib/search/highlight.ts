/** The API marks matches with U+0002 (start) and U+0003 (end), never HTML. Split into plain/hit runs. */
export type Run = { text: string; hit: boolean };

export function parseHighlight(s: string): Run[] {
  const runs: Run[] = [];
  let hit = false;
  for (const part of s.split(/([\u0002\u0003])/)) {
    if (part === "\u0002") hit = true;
    else if (part === "\u0003") hit = false;
    else if (part) runs.push({ text: part, hit });
  }
  return runs;
}
