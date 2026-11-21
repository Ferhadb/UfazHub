"use client";

import Link from "next/link";
import { useState } from "react";
import { Button, buttonClass } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { cn } from "@/components/ui/cn";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { errorInfo } from "@/lib/api/client";
import { useCollections, type Collection } from "@/lib/api/library";

// Literal classes so Tailwind sees them.
const spines = [
  "bg-collection text-ink",
  "bg-resource text-paper",
  "bg-article text-paper",
  "bg-question text-paper",
];

/** Collections as spines on a shelf: choose one and it pulls out, its card opens below. */
export function Spines({ collections }: { collections: Collection[] }) {
  const [open, setOpen] = useState<string | null>(null);
  const current = collections.find((c) => c.id === open);
  return (
    <>
      <ul
        aria-label="Shelf of collections"
        className="border-rule flex items-end gap-1 overflow-x-auto border-b-8 px-2 pt-10"
      >
        {collections.map((c, i) => {
          const pulled = c.id === open;
          return (
            <li key={c.id} className="shrink-0">
              <button
                type="button"
                aria-pressed={pulled}
                onClick={() => setOpen(pulled ? null : c.id)}
                aria-label={`${c.title}, ${c.call_number}, ${c.items.length} items`}
                style={{ height: `${10 + Math.min(c.items.length, 8) * 0.6}rem` }}
                className={cn(
                  "shadow-paper flex min-h-11 w-12 flex-col items-center justify-between rounded-t-sm px-1 py-2",
                  "transition-transform duration-(--duration-base) ease-(--ease-out) hover:-translate-y-3 focus-visible:-translate-y-3",
                  pulled && "-translate-y-6",
                  c.is_research ? "bg-research text-paper" : spines[i % spines.length],
                )}
              >
                <span className="text-step--1 font-mono tracking-widest [writing-mode:vertical-rl]">
                  {c.call_number.slice(-4)}
                </span>
                <span className="font-display line-clamp-1 max-h-[75%] [writing-mode:vertical-rl]">
                  {c.title}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      {current && (
        <section
          aria-live="polite"
          className="bg-card shadow-paper border-rule mt-6 rounded-md border p-5"
        >
          <p className="text-step--1 text-collection font-mono tracking-widest">
            {current.call_number}
          </p>
          <h2 className="font-display text-step-2">{current.title}</h2>
          <p className="text-muted mt-1">{current.description}</p>
          <ol className="mt-3 list-decimal ps-5">
            {current.items.slice(0, 5).map((it) => (
              <li key={it.item.id}>{it.item.title}</li>
            ))}
          </ol>
          {current.items.length > 5 && (
            <p className="text-muted mt-1">and {current.items.length - 5} more</p>
          )}
          <Link
            href={`/collections/${current.call_number}`}
            className={buttonClass("primary", "mt-4")}
          >
            Open collection
          </Link>
        </section>
      )}
    </>
  );
}

export function CollectionsView() {
  const q = useCollections({ sort: "latest" });
  const items = q.data?.pages.flatMap((p) => p.items) ?? [];
  return (
    <main id="main" className="relative z-10 mx-auto max-w-5xl px-4 py-8 sm:px-8 sm:py-12">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-step--1 text-collection font-mono tracking-widest uppercase">
            Catalogue · Collections
          </p>
          <h1 className="font-display text-step-4 mt-1">Collections</h1>
        </div>
        <Link href="/submit?type=collection" className={buttonClass("primary")}>
          Curate a collection
        </Link>
      </div>
      <div className="mt-8" aria-live="polite">
        {q.isPending ? (
          <Skeleton lines={4} />
        ) : q.isError ? (
          <Callout tone="danger" title="The shelf is stuck">
            <p>{errorInfo(q.error).message}</p>
            <Button className="mt-3" variant="secondary" onClick={() => q.refetch()}>
              Try again
            </Button>
          </Callout>
        ) : items.length === 0 ? (
          <EmptyState
            title="No collections yet"
            action={
              <Link href="/submit?type=collection" className={buttonClass("primary")}>
                Curate the first one
              </Link>
            }
          >
            Group resources and articles into a reading path.
          </EmptyState>
        ) : (
          <Spines collections={items} />
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
