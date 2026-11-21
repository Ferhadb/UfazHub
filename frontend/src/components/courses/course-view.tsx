"use client";

import Link from "next/link";
import { useState } from "react";
import { CardList, itemHref, NothingYet } from "@/components/cards/item-card";
import { Badge } from "@/components/ui/badge";
import { Button, buttonClass } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useCourseItems, type CardType } from "@/lib/api/cards";
import { useCourse } from "@/lib/api/courses";

const FILTERS = ["all", "resource", "article", "collection", "question"] as const;

export function CourseView({ slug }: { slug: string }) {
  const q = useCourse(slug);
  const [type, setType] = useState<(typeof FILTERS)[number]>("all");
  const items = useCourseItems(slug, type === "all" ? undefined : (type as CardType));

  if (q.isPending)
    return (
      <main id="main" className="relative z-10 mx-auto max-w-4xl px-4 py-10">
        <Skeleton lines={6} />
      </main>
    );
  if (q.isError) {
    const missing = (q.error as { status?: number }).status === 404;
    return (
      <main id="main" className="relative z-10 mx-auto max-w-4xl px-4 py-10">
        <EmptyState
          title={missing ? "No such course" : "The lecture hall is locked"}
          action={
            missing ? (
              <Link href="/courses" className={buttonClass("secondary")}>
                All courses
              </Link>
            ) : (
              <Button variant="secondary" onClick={() => q.refetch()}>
                Try again
              </Button>
            )
          }
        >
          {missing ? "It may have been renamed." : q.error.message}
        </EmptyState>
      </main>
    );
  }
  const c = q.data;
  return (
    <main id="main" className="relative z-10 mx-auto max-w-4xl px-4 py-8 sm:px-8 sm:py-12">
      <Link
        href="/courses"
        className="text-step--1 inline-flex min-h-11 items-center underline-offset-4 hover:underline"
      >
        All courses
      </Link>
      <p className="text-step--1 text-resource mt-2 font-mono tracking-widest uppercase">
        {c.program.name}
      </p>
      <h1 className="font-display text-step-4 mt-1">
        {c.name} <Badge tone="resource">{c.level}</Badge>
      </h1>
      {c.description && <p className="text-muted mt-2 max-w-prose">{c.description}</p>}
      <p className="text-step--1 mt-2 font-mono tabular-nums">
        {c.item_count} filed under this course
      </p>

      <section aria-labelledby="start" className="mt-10">
        <h2 id="start" className="font-display text-step-2">
          Start here
        </h2>
        {c.start_here.length === 0 ? (
          <p className="text-muted mt-2">
            No reading order yet. The editors will pin one once there is enough to read.
          </p>
        ) : (
          <ol className="mt-4 flex flex-col gap-4">
            {c.start_here.map((i, n) => (
              <li key={i.id} className="flex items-start gap-4">
                <span
                  aria-hidden="true"
                  className="font-display text-step-5 text-resource w-14 shrink-0 text-center leading-none"
                >
                  {n + 1}
                </span>
                <div className="bg-card shadow-paper border-rule min-w-0 flex-1 rounded-md border p-4">
                  <p className="text-step--1 text-muted font-mono tracking-widest">
                    {i.call_number} · {i.type}
                  </p>
                  <Link
                    href={itemHref(i)}
                    className="font-display text-step-1 inline-flex min-h-11 items-center underline-offset-4 hover:underline"
                  >
                    {i.title}
                  </Link>
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>

      <section aria-labelledby="all" className="mt-12">
        <h2 id="all" className="font-display text-step-2">
          Everything for this course
        </h2>
        <Tabs value={type} onValueChange={(v) => setType(v as typeof type)} className="mt-4">
          <TabsList aria-label="Type">
            {FILTERS.map((f) => (
              <TabsTrigger key={f} tint={f === "all" ? "resource" : f} value={f}>
                {f === "all" ? "All" : f[0]!.toUpperCase() + f.slice(1) + "s"}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
        <div className="mt-6">
          <CardList
            query={items}
            empty={
              <NothingYet>
                Nothing filed under this course yet. Be the first to leave a footprint.
              </NothingYet>
            }
          />
        </div>
      </section>
    </main>
  );
}
