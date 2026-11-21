import { readFileSync } from "node:fs";
import { join } from "node:path";

const css = readFileSync(join(__dirname, "tokens.css"), "utf8");

function block(selector: string): Record<string, string> {
  const start = css.indexOf(selector + " {");
  expect(start, selector).toBeGreaterThan(-1);
  const body = css.slice(
    start,
    css.indexOf("\n  }\n}", start) > -1 && selector.includes("not(")
      ? css.indexOf("\n  }\n}", start)
      : css.indexOf("\n}", start),
  );
  return Object.fromEntries(
    [...body.matchAll(/--([\w-]+):\s*([^;]+);/g)].map((m) => [m[1]!, m[2]!.trim()]),
  );
}

const light = block(":root");
const dark = block(':root[data-theme="dark"]');
const osDark = block(':root:not([data-theme="light"])');

function lum(hex: string): number {
  const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const [r, g, b] = c.map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)) as [
    number,
    number,
    number,
  ];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
function contrast(a: string, b: string): number {
  const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x) as [number, number];
  return (hi + 0.05) / (lo + 0.05);
}

const tints = ["resource", "article", "collection", "question", "research"].map((t) => `tint-${t}`);
// [foreground, background, minimum ratio]: 4.5 for text, 3 for UI/graphics.
const pairs: [string, string, number][] = [
  ["ink", "paper", 4.5],
  ["ink", "card", 4.5],
  ["muted", "paper", 4.5],
  ["muted", "card", 4.5],
  ["accent", "paper", 4.5],
  ["accent", "card", 4.5],
  ["accent-fg", "accent", 4.5],
  ["flame-text", "paper", 4.5],
  ["flame-text", "card", 4.5],
  ["on-highlighter", "highlighter", 4.5],
  ["danger", "paper", 4.5],
  ["success", "paper", 4.5],
  ["warning", "paper", 4.5],
  ["accent", "paper", 3],
  ["flame", "paper", 3],
  ...tints.flatMap((t): [string, string, number][] => [
    [t, "paper", 4.5],
    [t, "card", 4.5],
  ]),
];

describe.each([
  ["light", { ...light }],
  ["dark", { ...light, ...dark }],
])("%s theme contrast (WCAG AA)", (_name, vars) => {
  it.each(pairs)("%s on %s >= %s", (fg, bg, min) => {
    expect(contrast(vars[fg]!, vars[bg]!)).toBeGreaterThanOrEqual(min);
  });
});

it("OS-dark block matches the explicit dark block", () => {
  const strip = (o: Record<string, string>) =>
    Object.fromEntries(Object.entries(o).filter(([k]) => k !== "grain-opacity"));
  expect(strip(osDark)).toEqual(strip(dark));
});

it("defines the brand palette", () => {
  expect(light).toMatchObject({
    paper: "#f6f1e7",
    card: "#fbf8f1",
    ink: "#17140f",
    muted: "#6b6458",
  });
  expect(light.accent).toBe("#0e5a6b");
  expect(light.highlighter).toBe("#f4d35e");
});
