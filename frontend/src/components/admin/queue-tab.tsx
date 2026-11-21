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
import {
  REPORT_REASONS,
  useContentActions,
  useItemReports,
  useQueue,
  type ContentAction,
  type QueueFilters,
} from "@/lib/api/moderation";

type View = NonNullable<QueueFilters["view"]>;
const ACTIONS: Record<View, ContentAction["action"][]> = {
  reports: ["hide", "dismiss"],
  pending: ["approve", "hide"],
  hidden: ["unhide"],
};
const needsReason = (a: ContentAction["action"]) => a === "hide" || a === "unhide";

function Reports({ itemId }: { itemId: string }) {
  const { data, isLoading } = useItemReports(itemId);
  if (isLoading) return <Skeleton />;
  return (
    <ul className="mt-2 flex flex-col gap-1 text-sm">
      {data?.map((r) => (
        <li key={r.id}>
          <Badge>{r.reason.replace("_", " ")}</Badge> {r.reporter.display_name}
          {r.status !== "open" && <span className="text-muted"> ({r.status})</span>}
          {r.note && <span className="text-muted">: {r.note}</span>}
        </li>
      ))}
    </ul>
  );
}

export function QueueTab() {
  const [filters, setFilters] = useState<QueueFilters>({ view: "reports" });
  const view = filters.view ?? "reports";
  const q = useQueue(filters);
  const run = useContentActions();
  const toast = useToast();
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [open, setOpen] = useState<string | null>(null);
  const [ask, setAsk] = useState<ContentAction["action"] | null>(null);
  const items = q.data?.pages.flatMap((p) => p.items) ?? [];

  const toggle = (id: string) =>
    setPicked((s) => {
      const n = new Set(s);
      if (!n.delete(id)) n.add(id);
      return n;
    });

  const apply = async (action: ContentAction["action"], reason?: string) => {
    const out = await run.mutateAsync({ ids: [...picked], action, reason });
    setPicked(new Set());
    toast({
      title: `${out.done.length} done${out.failed.length ? `, ${out.failed.length} failed` : ""}`,
      description: out.failed.map((f) => f.message).join(" ") || undefined,
      tone: out.failed.length ? "danger" : "success",
    });
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <Select
          label="Show"
          value={view}
          onChange={(e) => {
            setPicked(new Set());
            setFilters({ ...filters, view: e.target.value as View });
          }}
        >
          <option value="reports">Reported</option>
          <option value="pending">Waiting for review</option>
          <option value="hidden">Hidden</option>
        </Select>
        <Select
          label="Type"
          value={filters.type ?? ""}
          onChange={(e) =>
            setFilters({ ...filters, type: (e.target.value || undefined) as QueueFilters["type"] })
          }
        >
          <option value="">All types</option>
          {["resource", "article", "collection", "question", "answer"].map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </Select>
        <Select
          label="Report reason"
          value={filters.reason ?? ""}
          disabled={view !== "reports"}
          onChange={(e) =>
            setFilters({
              ...filters,
              reason: (e.target.value || undefined) as QueueFilters["reason"],
            })
          }
        >
          <option value="">Any reason</option>
          {REPORT_REASONS.map(([v, t]) => (
            <option key={v} value={v}>
              {t}
            </option>
          ))}
        </Select>
      </div>

      <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Bulk actions">
        <span aria-live="polite" className="text-muted mr-2">
          {picked.size} selected
        </span>
        {ACTIONS[view].map((a) => (
          <Button
            key={a}
            variant={a === "hide" ? "danger" : "secondary"}
            disabled={picked.size === 0}
            loading={run.isPending}
            onClick={() => (needsReason(a) ? setAsk(a) : void apply(a))}
          >
            {a.charAt(0).toUpperCase() + a.slice(1)}
          </Button>
        ))}
      </div>

      {q.isLoading && <Skeleton />}
      {q.isError && <Callout tone="danger">Could not load the queue.</Callout>}
      {q.isSuccess && items.length === 0 && (
        <EmptyState title="Nothing here">The desk is clear.</EmptyState>
      )}
      <ul className="flex flex-col gap-2">
        {items.map((i) => (
          <li key={i.id} className="bg-card border-rule rounded-md border p-3">
            <div className="flex items-start gap-3">
              <input
                type="checkbox"
                className="mt-1 size-5"
                aria-label={`Select ${i.call_number}`}
                checked={picked.has(i.id)}
                onChange={() => toggle(i.id)}
              />
              <div className="min-w-0 flex-1">
                <Link href={hrefFor(i.call_number)} className="underline underline-offset-4">
                  {i.call_number} {i.title}
                </Link>
                <p className="text-muted text-sm">
                  by {i.author.display_name} · <Badge>{i.status.replace("_", " ")}</Badge>
                  {i.report_count > 0 && (
                    <>
                      {" "}
                      <Badge tone="flame">{i.report_count} reports</Badge>{" "}
                      {i.reasons.map((r) => r.replace("_", " ")).join(", ")}
                    </>
                  )}
                  {i.hidden_reason && <> · hidden: {i.hidden_reason}</>}
                </p>
                {i.report_count > 0 && (
                  <>
                    <Button
                      variant="ghost"
                      aria-expanded={open === i.id}
                      onClick={() => setOpen(open === i.id ? null : i.id)}
                    >
                      {open === i.id ? "Hide reports" : "Read reports"}
                    </Button>
                    {open === i.id && <Reports itemId={i.id} />}
                  </>
                )}
              </div>
            </div>
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
          title={`${ask === "hide" ? "Hide" : "Unhide"} ${picked.size} item(s)`}
          description={
            ask === "hide"
              ? "The author sees this reason and can appeal."
              : "The author is told the item is visible again."
          }
          confirmLabel={ask === "hide" ? "Hide" : "Unhide"}
          danger={ask === "hide"}
          onConfirm={(reason) => apply(ask, reason)}
        />
      )}
    </div>
  );
}
