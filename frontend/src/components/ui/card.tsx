import Link from "next/link";
import type { ReactNode } from "react";
import { cn, tintText, tintTop, type Tint } from "./cn";

/* Catalogue card: call number, coloured top edge, paper grain, optional rotated stamp.
 * Hover lifts and straightens it (transform only). The whole card is one link target. */
export function Card({
  callNumber,
  tint = "resource",
  title,
  headingLevel = 3,
  href,
  stamp,
  tilt = -0.8,
  children,
  className,
}: {
  callNumber: string;
  tint?: Tint;
  title: string;
  headingLevel?: 2 | 3 | 4;
  href?: string;
  stamp?: ReactNode;
  tilt?: number;
  children?: ReactNode;
  className?: string;
}) {
  const Heading = `h${headingLevel}` as const;
  return (
    <article
      style={{ rotate: `calc(${tilt} * var(--motion-rotate))` }}
      className={cn(
        "bg-card text-ink shadow-paper border-rule relative rounded-md border border-t-4 p-4",
        "transition-[transform,box-shadow,rotate] duration-(--duration-base) ease-(--ease-out)",
        "hover:shadow-lift focus-within:shadow-lift focus-within:rotate-0! hover:-translate-y-1 hover:rotate-0!",
        tintTop[tint],
        className,
      )}
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 rounded-[inherit]"
        style={{ backgroundImage: "var(--paper-grain)", opacity: "var(--grain-opacity)" }}
      />
      <p className={cn("text-step--1 relative font-mono tracking-widest", tintText[tint])}>
        {callNumber}
      </p>
      <Heading className="font-display text-step-1 relative mt-1">
        {href ? (
          <Link href={href} className="after:absolute after:-inset-4 after:content-['']">
            {title}
          </Link>
        ) : (
          title
        )}
      </Heading>
      {children && <div className="text-muted relative mt-2">{children}</div>}
      {stamp && <div className="absolute -top-3 right-3">{stamp}</div>}
    </article>
  );
}
