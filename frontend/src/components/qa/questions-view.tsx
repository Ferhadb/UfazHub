"use client";

import Link from "next/link";
import { useState } from "react";
import { Stamp } from "@/components/ui/badge";
import { Button, buttonClass } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { errorInfo } from "@/lib/api/client";
import { useQuestions, type Question, type QuestionFilters } from "@/lib/api/qa";

const VIEWS = {
  latest: { sort: "latest" },
  top: { sort: "top" },
  unanswered: { sort: "latest", unanswered: true },
} satisfies Record<string, QuestionFilters>;
type View = keyof typeof VIEWS;

function Row({ q }: { q: Question }) {
  return (
    <li className="bg-card shadow-paper border-rule border-t-question rounded-md border border-t-4 p-4">
      <p className="text-step--1 text-question font-mono tracking-widest">
        {q.call_number} · {q.topic}
      </p>
      <h2 className="font-display text-step-1">
        <Link href={`/questions/${q.call_number}`} className="underline-offset-4 hover:underline">
          {q.title}
        </Link>
      </h2>
      <p className="text-step--1 text-muted mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 font-mono tabular-nums">
        <span>{q.vote_score} votes</span>
        <span>
          {q.answer_count} {q.answer_count === 1 ? "answer" : "answers"}
        </span>
        <span>asked by {q.author.display_name}</span>
        {q.has_accepted && <Stamp tilt={-2}>✓ checked</Stamp>}
      </p>
    </li>
  );
}

export function QuestionsView() {
  const [view, setView] = useState<View>("latest");
  const q = useQuestions(VIEWS[view]);
  const items = q.data?.pages.flatMap((p) => p.items) ?? [];
  return (
    <main id="main" className="relative z-10 mx-auto max-w-3xl px-4 py-8 sm:px-8 sm:py-12">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-step--1 text-question font-mono tracking-widest uppercase">
            Catalogue · Questions
          </p>
          <h1 className="font-display text-step-4 mt-1">Exam hall</h1>
        </div>
        <Link href="/ask" className={buttonClass("primary")}>
          Ask a question
        </Link>
      </div>
      <Tabs value={view} onValueChange={(v) => setView(v as View)} className="mt-6">
        <TabsList aria-label="Order">
          <TabsTrigger tint="question" value="latest">
            Latest
          </TabsTrigger>
          <TabsTrigger tint="question" value="top">
            Top
          </TabsTrigger>
          <TabsTrigger tint="question" value="unanswered">
            Unanswered
          </TabsTrigger>
        </TabsList>
      </Tabs>
      <div className="mt-6" aria-live="polite">
        {q.isPending ? (
          <Skeleton lines={4} />
        ) : q.isError ? (
          <Callout tone="danger" title="The exam hall is locked">
            <p>{errorInfo(q.error).message}</p>
            <Button className="mt-3" variant="secondary" onClick={() => q.refetch()}>
              Try again
            </Button>
          </Callout>
        ) : items.length === 0 ? (
          <EmptyState
            title="No questions here"
            action={
              <Link href="/ask" className={buttonClass("primary")}>
                Ask the first one
              </Link>
            }
          >
            Nothing here yet. Be the first to leave a footprint.
          </EmptyState>
        ) : (
          <ul className="flex flex-col gap-4">
            {items.map((x) => (
              <Row key={x.id} q={x} />
            ))}
          </ul>
        )}
        {q.hasNextPage && (
          <div className="mt-8 flex justify-center">
            <Button
              variant="secondary"
              loading={q.isFetchingNextPage}
              onClick={() => q.fetchNextPage()}
            >
              Load more
            </Button>
          </div>
        )}
      </div>
    </main>
  );
}
