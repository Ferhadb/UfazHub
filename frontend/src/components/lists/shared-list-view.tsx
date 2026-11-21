"use client";

import Link from "next/link";
import { ItemCardView, NothingYet } from "@/components/cards/item-card";
import { Button, buttonClass } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useSharedList } from "@/lib/api/lists";

export function SharedListView({ token }: { token: string }) {
  const q = useSharedList(token);
  const shell = "relative z-10 mx-auto max-w-5xl px-4 py-8 sm:px-8 sm:py-12";
  if (q.isPending)
    return (
      <main id="main" className={shell}>
        <Skeleton lines={5} />
      </main>
    );
  if (q.isError) {
    const missing = (q.error as { status?: number }).status === 404;
    return (
      <main id="main" className={shell}>
        <EmptyState
          title={missing ? "This list is private" : "The shelf is stuck"}
          action={
            missing ? (
              <Link href="/" className={buttonClass("secondary")}>
                Back to the library
              </Link>
            ) : (
              <Button variant="secondary" onClick={() => q.refetch()}>
                Try again
              </Button>
            )
          }
        >
          {missing
            ? "The owner may have stopped sharing it, or the link is mistyped."
            : q.error.message}
        </EmptyState>
      </main>
    );
  }
  const l = q.data;
  return (
    <main id="main" className={shell}>
      <p className="text-step--1 text-collection font-mono tracking-widest uppercase">
        Reading list · by {l.owner.display_name}
      </p>
      <h1 className="font-display text-step-4 mt-1">{l.name}</h1>
      <div className="mt-8">
        {l.items.length === 0 ? (
          <NothingYet title="An empty list">Nothing on it yet.</NothingYet>
        ) : (
          <ul className="grid gap-6 sm:grid-cols-2">
            {l.items.map((i, n) => (
              <li key={i.id}>
                <ItemCardView item={i} tilt={n % 2 ? 0.6 : -0.6} />
              </li>
            ))}
          </ul>
        )}
        {l.next_cursor && (
          <p className="text-muted mt-6">Showing the first {l.items.length} items.</p>
        )}
      </div>
    </main>
  );
}
