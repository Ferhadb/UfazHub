"use client";

import Link from "next/link";
import { useState } from "react";
import { hrefFor } from "@/components/notifications/notifications-view";
import { ReasonDialog } from "@/components/moderation/reason-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { EmptyState } from "@/components/ui/empty-state";
import { Select } from "@/components/ui/field";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { useAdminAppeals, useResolveAppeal, type Appeal } from "@/lib/api/moderation";

type Status = "open" | "accepted" | "rejected";

export function AppealsTab() {
  const [status, setStatus] = useState<Status>("open");
  const q = useAdminAppeals(status);
  const resolve = useResolveAppeal();
  const toast = useToast();
  const [ask, setAsk] = useState<{ appeal: Appeal; decision: "accept" | "reject" } | null>(null);
  const appeals = q.data?.pages.flatMap((p) => p.items) ?? [];

  return (
    <div className="flex flex-col gap-4">
      <Select label="Status" value={status} onChange={(e) => setStatus(e.target.value as Status)}>
        <option value="open">Open</option>
        <option value="accepted">Accepted</option>
        <option value="rejected">Rejected</option>
      </Select>
      {q.isLoading && <Skeleton />}
      {q.isError && <Callout tone="danger">Could not load appeals.</Callout>}
      {q.isSuccess && appeals.length === 0 && <EmptyState title="No appeals" />}
      <ul className="flex flex-col gap-2">
        {appeals.map((a) => (
          <li key={a.id} className="bg-card border-rule rounded-md border p-3">
            <p>
              <Badge>{a.kind === "ban" ? "ban" : "hidden post"}</Badge> {a.user.display_name}
              {a.item && (
                <>
                  {" "}
                  <Link href={hrefFor(a.item.call_number)} className="underline underline-offset-4">
                    {a.item.call_number} {a.item.title}
                  </Link>
                </>
              )}
            </p>
            <blockquote className="border-rule mt-2 border-l-2 pl-3">{a.message}</blockquote>
            {a.response && (
              <p className="text-muted mt-2 text-sm">
                Answer ({a.status}): {a.response}
              </p>
            )}
            {a.status === "open" && (
              <div className="mt-2 flex gap-2">
                <Button onClick={() => setAsk({ appeal: a, decision: "accept" })}>Accept</Button>
                <Button
                  variant="secondary"
                  onClick={() => setAsk({ appeal: a, decision: "reject" })}
                >
                  Reject
                </Button>
              </div>
            )}
          </li>
        ))}
      </ul>
      {q.hasNextPage && (
        <Button
          variant="secondary"
          loading={q.isFetchingNextPage}
          onClick={() => q.fetchNextPage()}
        >
          Load more
        </Button>
      )}
      {ask && (
        <ReasonDialog
          open
          onOpenChange={(o) => !o && setAsk(null)}
          title={`${ask.decision === "accept" ? "Accept" : "Reject"} this appeal`}
          description={
            ask.decision === "accept"
              ? ask.appeal.kind === "ban"
                ? "The account is unbanned."
                : "The post becomes visible again."
              : "The post or ban stays in place."
          }
          label="Answer to the user"
          maxLength={1000}
          confirmLabel={ask.decision === "accept" ? "Accept" : "Reject"}
          onConfirm={async (response) => {
            await resolve.mutateAsync({ id: ask.appeal.id, decision: ask.decision, response });
            toast({ title: "Appeal resolved", tone: "success" });
          }}
        />
      )}
    </div>
  );
}
