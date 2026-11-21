import type { ReactNode } from "react";
import { Ornament } from "@/components/ui/ornament";
import { Stamp } from "@/components/ui/badge";

/** The library-card frame shared by every auth page. */
export function AuthShell({
  title,
  intro,
  stamp,
  children,
}: {
  title: string;
  intro?: string;
  stamp?: string;
  children: ReactNode;
}) {
  return (
    <main id="main" className="relative z-10 mx-auto w-full max-w-md px-4 py-10 sm:py-20">
      <div className="text-ink pointer-events-none absolute inset-x-0 top-0 -z-10 h-72 [mask-image:linear-gradient(black,transparent)]">
        <Ornament variant="star" strength={0.07} />
      </div>
      <div className="bg-card shadow-lift border-rule border-t-resource relative rounded-md border border-t-4 p-6 sm:p-8">
        {stamp && (
          <div className="absolute -top-4 right-4">
            <Stamp>{stamp}</Stamp>
          </div>
        )}
        <p className="text-step--1 text-resource font-mono tracking-widest uppercase">
          Library card
        </p>
        <h1 className="font-display text-step-3 mt-1">{title}</h1>
        {intro && <p className="text-muted mt-2">{intro}</p>}
        <div className="mt-6">{children}</div>
      </div>
    </main>
  );
}
