import type { ReactNode } from "react";
import { SuiteMark } from "@/components/gpa-button";
import { Stamp } from "@/components/ui/badge";
import { Ornament } from "@/components/ui/ornament";

const PERKS = [
  ["Find it", "Resources, notes and past papers filed by course."],
  ["Share it", "Publish an article or a collection in a few minutes."],
  ["Own it", "Earn reputation and stamps your classmates can see."],
];

/** Two-pane frame shared by every auth page: brand on the left, the form on the right. */
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
    <main
      id="main"
      className="relative z-10 mx-auto grid w-full max-w-5xl gap-0 px-4 py-8 sm:py-16 md:grid-cols-[1fr_26rem]"
    >
      <aside className="bg-card/60 border-rule relative hidden overflow-hidden rounded-l-md border border-r-0 p-10 md:block">
        <div className="text-ink pointer-events-none absolute inset-0 [mask-image:linear-gradient(black,transparent)]">
          <Ornament variant="star" strength={0.08} />
        </div>
        <div className="relative">
          <SuiteMark product="Hub" className="text-step-2" />
          <p className="font-display text-step-3 mt-8 max-w-xs">
            The library UFAZ students write themselves.
          </p>
          <ul className="mt-10 space-y-5">
            {PERKS.map(([h, d]) => (
              <li key={h}>
                <p className="text-resource text-step--1 font-mono tracking-widest uppercase">
                  {h}
                </p>
                <p className="text-muted mt-1 max-w-xs">{d}</p>
              </li>
            ))}
          </ul>
        </div>
      </aside>
      <div className="bg-card shadow-lift border-rule border-t-resource relative rounded-md border border-t-4 p-6 sm:p-8 md:rounded-l-none">
        {stamp && (
          <div className="absolute -top-4 right-4">
            <Stamp>{stamp}</Stamp>
          </div>
        )}
        <h1 className="font-display text-step-3">{title}</h1>
        {intro && <p className="text-muted mt-2">{intro}</p>}
        <div className="mt-6">{children}</div>
      </div>
    </main>
  );
}
