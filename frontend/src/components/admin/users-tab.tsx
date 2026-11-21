"use client";

import { useState } from "react";
import { ReasonDialog } from "@/components/moderation/reason-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { EmptyState } from "@/components/ui/empty-state";
import { Input, Select } from "@/components/ui/field";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import {
  useAdminUsers,
  useUserAction,
  type AdminUser,
  type UserFilters,
} from "@/lib/api/moderation";

type Pending = {
  user: AdminUser;
  title: string;
  danger?: boolean;
  change: { status: AdminUser["status"] } | { role: AdminUser["role"] };
};

export function UsersTab({ selfId }: { selfId: string }) {
  const [draft, setDraft] = useState("");
  const [filters, setFilters] = useState<UserFilters>({});
  const q = useAdminUsers(filters);
  const act = useUserAction();
  const toast = useToast();
  const [pending, setPending] = useState<Pending | null>(null);
  const users = q.data?.pages.flatMap((p) => p.items) ?? [];
  const set = (patch: Partial<UserFilters>) => setFilters({ ...filters, ...patch });

  return (
    <div className="flex flex-col gap-4">
      <form
        className="grid gap-3 sm:grid-cols-[2fr_1fr_1fr_auto] sm:items-end"
        onSubmit={(e) => {
          e.preventDefault();
          set({ q: draft.trim() || undefined });
        }}
      >
        <Input
          label="Search name or email"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
        />
        <Select
          label="Role"
          value={filters.role ?? ""}
          onChange={(e) => set({ role: (e.target.value || undefined) as UserFilters["role"] })}
        >
          <option value="">Any role</option>
          <option value="user">user</option>
          <option value="verified_ufazian">verified ufazian</option>
          <option value="admin">admin</option>
        </Select>
        <Select
          label="Status"
          value={filters.status ?? ""}
          onChange={(e) => set({ status: (e.target.value || undefined) as UserFilters["status"] })}
        >
          <option value="">Any status</option>
          <option value="active">active</option>
          <option value="muted">muted</option>
          <option value="banned">banned</option>
        </Select>
        <Button type="submit">Search</Button>
      </form>

      {q.isLoading && <Skeleton />}
      {q.isError && <Callout tone="danger">Could not load users.</Callout>}
      {q.isSuccess && users.length === 0 && <EmptyState title="No such user" />}
      <ul className="flex flex-col gap-2">
        {users.map((u) => (
          <li key={u.id} className="bg-card border-rule rounded-md border p-3">
            <p className="font-semibold">{u.display_name}</p>
            <p className="text-muted text-sm">
              {u.email} · {u.reputation} rep
            </p>
            <p className="mt-1 flex flex-wrap gap-2">
              <Badge>{u.role.replace("_", " ")}</Badge>
              <Badge tone={u.status === "active" ? "neutral" : "flame"}>{u.status}</Badge>
            </p>
            {u.id !== selfId && (
              <div className="mt-2 flex flex-wrap gap-2">
                {u.role !== "admin" && u.status === "active" && (
                  <>
                    <Button
                      variant="secondary"
                      onClick={() =>
                        setPending({ user: u, title: "Mute", change: { status: "muted" } })
                      }
                    >
                      Mute
                    </Button>
                    <Button
                      variant="danger"
                      onClick={() =>
                        setPending({
                          user: u,
                          title: "Ban",
                          danger: true,
                          change: { status: "banned" },
                        })
                      }
                    >
                      Ban
                    </Button>
                  </>
                )}
                {u.status !== "active" && (
                  <Button
                    variant="secondary"
                    onClick={() =>
                      setPending({
                        user: u,
                        title: u.status === "banned" ? "Unban" : "Unmute",
                        change: { status: "active" },
                      })
                    }
                  >
                    {u.status === "banned" ? "Unban" : "Unmute"}
                  </Button>
                )}
                {(["user", "verified_ufazian", "admin"] as const)
                  .filter((r) => r !== u.role)
                  .map((r) => (
                    <Button
                      key={r}
                      variant="ghost"
                      onClick={() =>
                        setPending({
                          user: u,
                          title: `Make ${r.replace("_", " ")}`,
                          change: { role: r },
                        })
                      }
                    >
                      Make {r.replace("_", " ")}
                    </Button>
                  ))}
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

      {pending && (
        <ReasonDialog
          open
          onOpenChange={(o) => !o && setPending(null)}
          title={`${pending.title}: ${pending.user.display_name}`}
          description="The reason is saved in the audit log and shown to the user."
          confirmLabel={pending.title}
          danger={pending.danger}
          onConfirm={async (reason) => {
            await act.mutateAsync({ id: pending.user.id, reason, ...pending.change });
            toast({ title: "Saved", tone: "success" });
          }}
        />
      )}
    </div>
  );
}
