"use client";

import Link from "next/link";
import { Comments } from "@/components/comments/comments";
import { ResourceActions } from "@/components/resources/actions";
import { Badge } from "@/components/ui/badge";
import { Button, buttonClass } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Marginalia } from "@/components/ui/marginalia";
import { Skeleton } from "@/components/ui/skeleton";
import { useCollection } from "@/lib/api/library";

export function CollectionDetail({ callNumber }: { callNumber: string }) {
  const q = useCollection(callNumber);
  const shell = "relative z-10 mx-auto max-w-3xl px-4 py-8 sm:py-12";
  if (q.isPending)
    return (
      <main id="main" className={shell}>
        <Skeleton lines={6} />
      </main>
    );
  if (q.isError)
    return (
      <main id="main" className={shell}>
        <EmptyState
          title={
            (q.error as { status?: number }).status === 404
              ? "No such collection"
              : "The shelf is stuck"
          }
          action={
            <Link href="/collections" className={buttonClass("secondary")}>
              All collections
            </Link>
          }
        >
          {q.error.message}
        </EmptyState>
        <Button className="mt-4" variant="ghost" onClick={() => q.refetch()}>
          Try again
        </Button>
      </main>
    );
  const c = q.data;
  return (
    <main id="main" className={shell}>
      <p className="text-step--1 text-collection font-mono tracking-widest">{c.call_number}</p>
      <h1 className="font-display text-step-4 mt-1">{c.title}</h1>
      <p className="text-muted mt-2">
        Curated by {c.author.display_name} · {c.items.length} items
      </p>
      <p className="mt-4">{c.description}</p>
      <ResourceActions resource={c} className="border-rule mt-4 border-t pt-2" />
      <ol className="mt-8 flex flex-col gap-8">
        {c.items.map((it, i) => (
          <li key={it.item.id} className="grid gap-3 sm:grid-cols-[1fr_14rem]">
            <div>
              <p className="text-muted font-mono">
                {i + 1}. {it.item.call_number}
              </p>
              <h2 className="font-display text-step-1">
                <Link
                  href={`/${it.item.type}s/${it.item.call_number}`}
                  className="underline-offset-4 hover:underline"
                >
                  {it.item.title}
                </Link>
              </h2>
              <p className="text-muted mt-1">{it.item.description}</p>
              <Badge tone={it.item.type === "article" ? "article" : "resource"}>
                {it.item.type}
              </Badge>
            </div>
            {it.note && (
              <div className="relative">
                <Marginalia>{it.note}</Marginalia>
              </div>
            )}
          </li>
        ))}
      </ol>
      <Comments itemId={c.id} count={c.comment_count} />
    </main>
  );
}
