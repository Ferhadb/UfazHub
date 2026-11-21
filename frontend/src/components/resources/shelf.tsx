import Link from "next/link";
import { cn } from "@/components/ui/cn";
import type { Resource } from "@/lib/api/content";

// Literal classes so Tailwind sees them.
const spine = {
  beginner: "bg-resource text-paper",
  intermediate: "bg-collection text-ink",
  advanced: "bg-question text-paper",
} as const;

/** Resources as book spines on a shelf: height follows time commitment; hover or focus pulls one out. */
export function Shelf({ resources }: { resources: Resource[] }) {
  return (
    <ul
      aria-label="Shelf of resources"
      className="border-rule flex items-end gap-1 overflow-x-auto border-b-8 px-2 pt-8 pb-0"
    >
      {resources.map((r) => {
        const h = 9 + Math.min(Math.round((r.time_commitment_minutes ?? 120) / 300), 5); // rem
        return (
          <li key={r.id} className="shrink-0">
            <Link
              href={`/resources/${r.call_number}`}
              aria-label={`${r.title}, ${r.call_number}, ${r.difficulty}`}
              style={{ height: `${h}rem` }}
              className={cn(
                "shadow-paper flex min-h-11 w-12 flex-col items-center justify-between gap-2 rounded-t-sm px-1 py-3",
                "transition-transform duration-(--duration-base) ease-(--ease-out) hover:-translate-y-3 focus-visible:-translate-y-3",
                r.is_research ? "bg-research text-paper" : spine[r.difficulty],
              )}
            >
              <span className="text-step--1 font-mono tracking-widest [writing-mode:vertical-rl]">
                {r.call_number.slice(-4)}
              </span>
              <span className="font-display text-step-0 max-h-[75%] overflow-hidden text-ellipsis whitespace-nowrap [writing-mode:vertical-rl]">
                {r.title}
              </span>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
