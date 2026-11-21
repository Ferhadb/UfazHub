import { cn } from "./cn";

/** A blank index card with a slow shimmer. Announced once as "Loading". */
export function Skeleton({ lines = 3, className }: { lines?: number; className?: string }) {
  return (
    <div
      role="status"
      aria-busy="true"
      className={cn(
        "bg-card shadow-paper border-rule relative overflow-hidden rounded-md border border-t-4 p-4",
        "shimmer",
        className,
      )}
    >
      <span className="sr-only">Loading…</span>
      <div aria-hidden="true" className="flex flex-col gap-3">
        <div className="bg-rule/60 h-4 w-1/4 rounded-sm" />
        {Array.from({ length: lines }, (_, i) => (
          <div
            key={i}
            className="bg-rule/40 h-3 rounded-sm"
            style={{ width: `${i === lines - 1 ? 55 : 100 - ((i * 7) % 15)}%` }}
          />
        ))}
      </div>
    </div>
  );
}
