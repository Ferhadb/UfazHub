"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { errorInfo } from "@/lib/api/client";
import { usePrograms } from "@/lib/api/courses";

export function CoursesView() {
  const q = usePrograms();
  return (
    <main id="main" className="relative z-10 mx-auto max-w-5xl px-4 py-8 sm:px-8 sm:py-12">
      <p className="text-step--1 text-resource font-mono tracking-widest uppercase">
        Catalogue · Courses
      </p>
      <h1 className="font-display text-step-4 mt-1">Pick your course</h1>
      <p className="text-muted mt-2 max-w-prose">
        Every course page keeps what students filed under it, with a short path for where to begin.
      </p>
      <div className="mt-8" aria-live="polite">
        {q.isPending ? (
          <Skeleton lines={5} />
        ) : q.isError ? (
          <Callout tone="danger" title="The timetable is missing">
            <p>{errorInfo(q.error).message}</p>
            <Button className="mt-3" variant="secondary" onClick={() => q.refetch()}>
              Try again
            </Button>
          </Callout>
        ) : q.data.length === 0 ? (
          <EmptyState title="No courses yet">
            The faculty office has not filed the timetable. Check back soon.
          </EmptyState>
        ) : (
          q.data.map((p, n) => (
            <section key={p.slug} aria-labelledby={`p-${p.slug}`} className="mt-10 first:mt-0">
              <div className="flex items-baseline gap-4">
                <span aria-hidden="true" className="font-display text-step-5 text-rule">
                  {String(n + 1).padStart(2, "0")}
                </span>
                <div>
                  <h2 id={`p-${p.slug}`} className="font-display text-step-2">
                    {p.name}
                  </h2>
                  {p.description && <p className="text-muted">{p.description}</p>}
                </div>
              </div>
              {p.courses.length === 0 ? (
                <p className="text-muted mt-3">No courses in this program yet.</p>
              ) : (
                <ul className="mt-3 flex flex-wrap gap-3">
                  {p.courses.map((c) => (
                    <li key={c.slug}>
                      <Link
                        href={`/courses/${c.slug}`}
                        className="bg-card shadow-paper border-rule border-t-resource inline-flex min-h-11 items-center gap-2 rounded-md border border-t-4 px-4 py-2 hover:-translate-y-0.5"
                      >
                        {c.name} <Badge tone="resource">{c.level}</Badge>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          ))
        )}
      </div>
    </main>
  );
}
