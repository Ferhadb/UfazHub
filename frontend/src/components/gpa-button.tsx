"use client";
import { cn } from "@/components/ui/cn";

import { buttonClass } from "@/components/ui/button";
import { startGpaSignIn } from "@/lib/gpa";

/** The two-tone mark both sites share: UFAZ in ink, the product in its own colour. */
export function SuiteMark({ product, className }: { product: "GPA" | "Hub"; className?: string }) {
  return (
    <span className={`font-display inline-flex items-baseline gap-1 ${className ?? ""}`}>
      UFAZ <span className="text-flame-text">{product}</span>
    </span>
  );
}

export function GpaButton({
  next,
  label,
  className,
}: {
  next: string;
  label: string;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={() => startGpaSignIn(next)}
      className={buttonClass("primary", cn("w-full gap-2", className))}
    >
      {label}
      <span aria-hidden>↗</span>
    </button>
  );
}
