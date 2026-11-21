"use client";

import Link from "next/link";
import { useState } from "react";
import { hrefFor } from "@/components/notifications/notifications-view";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import {
  useAppealContent,
  useMyAppeals,
  useMyModeration,
  type ModerationEvent,
} from "@/lib/api/moderation";
import { ReasonDialog } from "./reason-dialog";

const LABEL: Record<string, string> = {
  "content.hide": "Post hidden",
  "content.unhide": "Post made visible again",
  "content.approve": "Post approved",
  "user.mute": "Account muted",
  "user.unmute": "Account unmuted",
  "user.ban": "Account suspended",
  "user.unban": "Suspension lifted",
};

/** Everything moderators did to the signed-in user's account or posts, with the reason, plus appeals. */
export function ModerationHistory() {
  const q = useMyModeration();
  const appeals = useMyAppeals();
  const appeal = useAppealContent();
  const toast = useToast();
  const [target, setTarget] = useState<ModerationEvent["item"]>(null);
  const events = q.data?.pages.flatMap((p) => p.items) ?? [];
  const openFor = new Set(
    appeals.data?.filter((a) => a.status === "open").map((a) => a.item?.id) ?? [],
  );
  // Only the latest event per post decides whether it can be appealed right now.
  const latest = new Map<string, string>();
  for (const e of events) if (e.item && !latest.has(e.item.id)) latest.set(e.item.id, e.id);

  return (
    <section
      aria-labelledby="moderation"
      className="bg-card shadow-paper border-rule rounded-md border p-4"
    >
      <h2 id="moderation" className="font-display text-step-1">
        Moderation history
      </h2>
      {q.isLoading && <Skeleton />}
      {q.isSuccess && events.length === 0 && (
        <p className="text-muted mt-2">Nothing here. Your record is clean.</p>
      )}
      <ul className="mt-2 flex flex-col gap-3">
        {events.map((e) => (
          <li key={e.id} className="border-rule border-b pb-3 last:border-b-0">
            <p className="font-semibold">{LABEL[e.action] ?? e.action}</p>
            {e.item && (
              <Link href={hrefFor(e.item.call_number)} className="underline underline-offset-4">
                {e.item.call_number} {e.item.title}
              </Link>
            )}
            {e.reason && <p className="text-muted">Reason: {e.reason}</p>}
            <time dateTime={e.created_at} className="text-step--1 text-muted block font-mono">
              {new Date(e.created_at).toLocaleDateString()}
            </time>
            {e.action === "content.hide" &&
              e.item?.status === "hidden" &&
              latest.get(e.item.id) === e.id &&
              (openFor.has(e.item.id) ? (
                <Badge className="mt-1">Appeal sent</Badge>
              ) : (
                <Button variant="secondary" className="mt-1" onClick={() => setTarget(e.item)}>
                  Appeal
                </Button>
              ))}
          </li>
        ))}
      </ul>
      {q.hasNextPage && (
        <Button
          variant="secondary"
          className="mt-3"
          loading={q.isFetchingNextPage}
          onClick={() => q.fetchNextPage()}
        >
          Load more
        </Button>
      )}
      {!!appeals.data?.length && (
        <>
          <h3 className="font-display text-step-0 mt-4">Your appeals</h3>
          <ul className="mt-1 flex flex-col gap-2">
            {appeals.data.map((a) => (
              <li key={a.id}>
                <Badge tone={a.status === "accepted" ? "article" : "neutral"}>{a.status}</Badge>{" "}
                {a.item ? `${a.item.call_number} ${a.item.title}` : "Account suspension"}
                {a.response && <span className="text-muted"> — {a.response}</span>}
              </li>
            ))}
          </ul>
        </>
      )}
      {target && (
        <ReasonDialog
          open
          onOpenChange={(o) => !o && setTarget(null)}
          title={`Appeal: ${target.title}`}
          description="Explain why this post should be visible again. A moderator will answer."
          label="Your message"
          minLength={10}
          maxLength={1000}
          confirmLabel="Send appeal"
          onConfirm={async (message) => {
            await appeal.mutateAsync({ itemId: target.id, message });
            toast({ title: "Appeal sent", tone: "success" });
          }}
        />
      )}
    </section>
  );
}
