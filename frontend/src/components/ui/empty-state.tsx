import type { ReactNode } from "react";
import { EmptyDrawer } from "./illustrations";
import { Ornament } from "./ornament";

/** Illustration + a title + a witty line + an optional action. */
export function EmptyState({
  title,
  children,
  illustration = <EmptyDrawer className="text-ink size-32" />,
  action,
}: {
  title: string;
  children?: ReactNode;
  illustration?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className="relative flex flex-col items-center gap-3 overflow-hidden rounded-lg px-6 py-12 text-center">
      <Ornament variant="star" className="text-ink absolute inset-0 -z-10" strength={0.05} />
      {illustration}
      <h2 className="font-display text-step-2">{title}</h2>
      {children && <p className="text-muted max-w-sm">{children}</p>}
      {action}
    </section>
  );
}
