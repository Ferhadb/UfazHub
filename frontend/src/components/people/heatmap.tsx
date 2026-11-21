import type { Profile } from "@/lib/api/people";

const CELL = 14;
const WEEKS = 53;
const DAY_MS = 86_400_000;
const iso = (d: Date) => d.toISOString().slice(0, 10);

/** Cross-stitch level 0-4 for a day's count. */
export const level = (n: number) => (n <= 0 ? 0 : n === 1 ? 1 : n === 2 ? 2 : n <= 4 ? 3 : 4);

/** The last 53 weeks of activity as cross-stitches on a dashed grid (UTC days, like the API). */
export function Heatmap({
  activity,
  today = new Date(),
}: {
  activity: Profile["activity"];
  today?: Date;
}) {
  const counts = new Map(activity.map((a) => [a.day, a.count]));
  const end = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate()));
  // Columns are weeks starting Sunday; the last column holds today.
  const start = new Date(end.getTime() - (end.getUTCDay() + (WEEKS - 1) * 7) * DAY_MS);
  const total = activity.reduce((n, a) => n + a.count, 0);
  const cells: { x: number; y: number; day: string; n: number }[] = [];
  for (let w = 0; w < WEEKS; w++)
    for (let d = 0; d < 7; d++) {
      const date = new Date(start.getTime() + (w * 7 + d) * DAY_MS);
      if (date > end) continue;
      const day = iso(date);
      cells.push({ x: w * CELL, y: d * CELL, day, n: counts.get(day) ?? 0 });
    }
  return (
    <figure className="overflow-x-auto">
      <svg
        role="img"
        aria-label={`${total} ${total === 1 ? "contribution" : "contributions"} in the last year`}
        viewBox={`0 0 ${WEEKS * CELL} ${7 * CELL}`}
        width={WEEKS * CELL}
        height={7 * CELL}
        className="text-accent min-w-[46rem]"
      >
        {cells.map((c) => (
          <g key={c.day}>
            <title>{`${c.n} on ${c.day}`}</title>
            <rect
              x={c.x + 1}
              y={c.y + 1}
              width={CELL - 2}
              height={CELL - 2}
              rx={2}
              fill="none"
              stroke="currentColor"
              strokeOpacity={0.25}
              strokeDasharray="2 2"
            />
            {c.n > 0 && (
              <path
                d={`M${c.x + 3.5} ${c.y + 3.5}L${c.x + CELL - 3.5} ${c.y + CELL - 3.5}M${c.x + CELL - 3.5} ${c.y + 3.5}L${c.x + 3.5} ${c.y + CELL - 3.5}`}
                stroke="currentColor"
                strokeLinecap="round"
                strokeWidth={0.8 + level(c.n) * 0.35}
                strokeOpacity={0.4 + level(c.n) * 0.15}
              />
            )}
          </g>
        ))}
      </svg>
      <figcaption className="text-step--1 text-muted mt-1 font-mono tracking-widest uppercase">
        Stitched by day, last 12 months
      </figcaption>
    </figure>
  );
}
