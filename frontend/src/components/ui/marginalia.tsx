import type { ReactNode } from "react";
import { cn } from "./cn";

/* A student's note in the margin, in the one place Caveat is allowed.
 * Place inside a `relative` block: from `lg` it sits in the right margin with a hand-drawn
 * connector; below that it becomes an inline bubble so nothing overflows a 360px screen. */
export function Marginalia({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <aside
      aria-label="Margin note"
      className={cn(
        "font-script text-step-1 text-accent border-accent/50 relative mt-3 rounded-lg border border-dashed px-3 py-2 leading-snug",
        "lg:absolute lg:top-0 lg:left-full lg:mt-0 lg:ml-10 lg:w-52 lg:border-0 lg:p-0",
        className,
      )}
    >
      <svg
        aria-hidden="true"
        focusable="false"
        viewBox="0 0 40 16"
        className="absolute top-3 right-full hidden h-4 w-10 lg:block"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      >
        <path d="M2 10c8 5 14-8 22-3s9 2 14-2M33 3l5 2-4 4" />
      </svg>
      {children}
    </aside>
  );
}
