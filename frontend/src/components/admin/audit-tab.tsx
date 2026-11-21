"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/field";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuditLog, type AuditFilters } from "@/lib/api/moderation";

export function AuditTab() {
  const [draft, setDraft] = useState({ action: "", target_type: "", target_id: "" });
  const [filters, setFilters] = useState<AuditFilters>({});
  const q = useAuditLog(filters);
  const rows = q.data?.pages.flatMap((p) => p.items) ?? [];

  return (
    <div className="flex flex-col gap-4">
      <form
        className="grid gap-3 sm:grid-cols-4 sm:items-end"
        onSubmit={(e) => {
          e.preventDefault();
          setFilters({
            action: draft.action.trim() || undefined,
            target_type: draft.target_type.trim() || undefined,
            target_id: draft.target_id.trim() || undefined,
          });
        }}
      >
        <Input
          label="Action"
          placeholder="content.hide"
          value={draft.action}
          onChange={(e) => setDraft({ ...draft, action: e.target.value })}
        />
        <Input
          label="Target type"
          placeholder="user"
          value={draft.target_type}
          onChange={(e) => setDraft({ ...draft, target_type: e.target.value })}
        />
        <Input
          label="Target id"
          value={draft.target_id}
          onChange={(e) => setDraft({ ...draft, target_id: e.target.value })}
        />
        <Button type="submit">Filter</Button>
      </form>
      {q.isLoading && <Skeleton />}
      {q.isError && <Callout tone="danger">Could not load the log.</Callout>}
      {q.isSuccess && rows.length === 0 && <EmptyState title="Nothing logged" />}
      <ol className="flex flex-col gap-2">
        {rows.map((r) => (
          <li key={r.id} className="bg-card border-rule rounded-md border p-3 text-sm">
            <p>
              <span className="font-mono font-semibold">{r.action}</span> by{" "}
              {r.actor?.display_name ?? "system"} on {r.target_type}{" "}
              <span className="font-mono break-all">{r.target_id}</span>
            </p>
            <time dateTime={r.created_at} className="text-muted font-mono">
              {new Date(r.created_at).toLocaleString()}
            </time>
            {r.reason && <p className="mt-1">Reason: {r.reason}</p>}
            {(r.before || r.after) && (
              <pre className="bg-ink/5 mt-1 overflow-x-auto rounded p-2 font-mono text-xs">
                {JSON.stringify({ before: r.before, after: r.after }, null, 2)}
              </pre>
            )}
          </li>
        ))}
      </ol>
      {q.hasNextPage && (
        <Button
          variant="secondary"
          loading={q.isFetchingNextPage}
          onClick={() => q.fetchNextPage()}
        >
          Load more
        </Button>
      )}
    </div>
  );
}
