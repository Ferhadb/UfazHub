"use client";

import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { cn } from "@/components/ui/cn";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/toggles";
import { errorInfo } from "@/lib/api/client";
import {
  useDigestSetting,
  useMarkRead,
  useNotifications,
  type Notification,
} from "@/lib/api/notifications";

const PAGE = { RES: "resources", ART: "articles", COL: "collections", QST: "questions" } as const;
export const hrefFor = (callNumber: string) =>
  `/${PAGE[callNumber.slice(0, 3) as keyof typeof PAGE] ?? "resources"}/${callNumber}`;

export function describe(n: Notification): string {
  const who = n.actor?.display_name ?? "Someone";
  switch (n.kind) {
    case "reply":
      return `${who} replied on`;
    case "answer":
      return `${who} answered`;
    case "answer_accepted":
      return `${who} checked your answer on`;
    case "vote_milestone":
      return `${n.message} on`;
    default:
      return `Moderation, ${n.message}:`;
  }
}

function Row({ n, onOpen }: { n: Notification; onOpen: (n: Notification) => void }) {
  return (
    <li
      className={cn(
        "bg-card border-rule flex items-start gap-3 rounded-md border p-4",
        !n.read && "border-s-flame border-s-4",
      )}
    >
      <p className="min-w-0 flex-1">
        {!n.read && <span className="sr-only">Unread. </span>}
        {describe(n)}{" "}
        <Link
          href={hrefFor(n.call_number)}
          onClick={() => onOpen(n)}
          className="underline underline-offset-4"
        >
          {n.call_number} {n.title}
        </Link>
        <time
          dateTime={n.created_at}
          className="text-step--1 text-muted mt-1 block font-mono tabular-nums"
        >
          {new Date(n.created_at).toLocaleString(undefined, {
            day: "numeric",
            month: "short",
            hour: "2-digit",
            minute: "2-digit",
          })}
        </time>
      </p>
    </li>
  );
}

export function NotificationsView() {
  const [unreadOnly, setUnreadOnly] = useState(false);
  const q = useNotifications(unreadOnly);
  const mark = useMarkRead();
  const digest = useDigestSetting();
  const items = q.data?.pages.flatMap((p) => p.items) ?? [];
  return (
    <main id="main" className="relative z-10 mx-auto max-w-3xl px-4 py-8 sm:px-8 sm:py-12">
      <h1 className="font-display text-step-4">Notifications</h1>
      <div className="mt-6 flex flex-wrap items-center gap-4">
        <Switch
          label="Unread only"
          checked={unreadOnly}
          onCheckedChange={(v) => setUnreadOnly(Boolean(v))}
        />
        <Switch
          label="Email me a daily digest"
          checked={digest.query.data?.email_digest ?? false}
          disabled={!digest.query.data}
          onCheckedChange={(v) => digest.set.mutate(Boolean(v))}
        />
        <Button variant="secondary" loading={mark.isPending} onClick={() => mark.mutate(undefined)}>
          Mark all read
        </Button>
      </div>
      <div className="mt-6" aria-live="polite">
        {q.isPending ? (
          <Skeleton lines={4} />
        ) : q.isError ? (
          <Callout tone="danger" title="The post office is closed">
            <p>{errorInfo(q.error).message}</p>
            <Button className="mt-3" variant="secondary" onClick={() => q.refetch()}>
              Try again
            </Button>
          </Callout>
        ) : items.length === 0 ? (
          <EmptyState title="All quiet">
            Nothing here yet. Be the first to leave a footprint.
          </EmptyState>
        ) : (
          <ul className="flex flex-col gap-3">
            {items.map((n) => (
              <Row key={n.id} n={n} onOpen={(x) => !x.read && mark.mutate([x.id])} />
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
