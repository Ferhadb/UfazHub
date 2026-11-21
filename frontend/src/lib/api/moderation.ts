"use client";

import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, errorInfo } from "./client";
import type { components, operations } from "./schema";
import { useSession } from "@/lib/auth/use-session";

export type QueueItem = components["schemas"]["QueueItem"];
export type AdminUser = components["schemas"]["UserAdminOut"];
export type Appeal = components["schemas"]["AppealOut"];
export type AuditEntry = components["schemas"]["AuditOut"];
export type ReportEntry = components["schemas"]["ReportOut"];
export type ModerationEvent = components["schemas"]["ModerationEvent"];
export type ContentAction = components["schemas"]["ContentAction"];
export type ReportReason = components["schemas"]["ReportIn"]["reason"];
export type QueueFilters = NonNullable<
  operations["queue_api_admin_queue_get"]["parameters"]["query"]
>;
export type UserFilters = NonNullable<
  operations["users_api_admin_users_get"]["parameters"]["query"]
>;
export type AuditFilters = NonNullable<
  operations["audit_log_api_admin_audit_get"]["parameters"]["query"]
>;

export const REPORT_REASONS: [ReportReason, string][] = [
  ["spam", "Spam or advertising"],
  ["offensive", "Offensive or abusive"],
  ["copyright", "Copyright problem"],
  ["inaccurate", "Inaccurate or misleading"],
  ["broken_link", "Broken link"],
  ["off_topic", "Off topic"],
  ["other", "Something else"],
];

const fail = (error: unknown): never => {
  throw new Error(errorInfo(error).message);
};

export function useReport(itemId: string) {
  return useMutation({
    mutationFn: async (body: { reason: ReportReason; note: string }) => {
      const { error } = await api.POST("/api/content/{item_id}/report", {
        params: { path: { item_id: itemId } },
        body,
      });
      if (error) fail(error);
    },
  });
}

// --- admin: queue, content actions ----------------------------------------------------------
export function useQueue(filters: QueueFilters) {
  return useInfiniteQuery({
    queryKey: ["admin", "queue", filters],
    initialPageParam: undefined as string | undefined,
    queryFn: async ({ pageParam }) => {
      const { data, error } = await api.GET("/api/admin/queue", {
        params: { query: { ...filters, limit: 20, cursor: pageParam } },
      });
      if (!data) throw error;
      return data;
    },
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  });
}

export function useItemReports(itemId: string | null) {
  return useQuery({
    queryKey: ["admin", "reports", itemId],
    enabled: !!itemId,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/admin/content/{item_id}/reports", {
        params: { path: { item_id: itemId! } },
      });
      if (!data) throw error;
      return data;
    },
  });
}

export function useContentActions() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: ContentAction) => {
      const { data, error } = await api.POST("/api/admin/content/actions", { body });
      if (!data) return fail(error);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin"] }),
  });
}

// --- admin: users ----------------------------------------------------------------------------
export function useAdminUsers(filters: UserFilters) {
  return useInfiniteQuery({
    queryKey: ["admin", "users", filters],
    initialPageParam: undefined as string | undefined,
    queryFn: async ({ pageParam }) => {
      const { data, error } = await api.GET("/api/admin/users", {
        params: { query: { ...filters, limit: 20, cursor: pageParam } },
      });
      if (!data) throw error;
      return data;
    },
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  });
}

export function useUserAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (
      v: { id: string; reason: string } & (
        { status: AdminUser["status"] } | { role: AdminUser["role"] }
      ),
    ) => {
      const { id, reason } = v;
      const params = { path: { user_id: id } };
      const res =
        "status" in v
          ? await api.PUT("/api/admin/users/{user_id}/status", {
              params,
              body: { status: v.status as "active", reason },
            })
          : await api.PUT("/api/admin/users/{user_id}/role", {
              params,
              body: { role: v.role as "user", reason },
            });
      if (!res.data) return fail(res.error);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin"] }),
  });
}

// --- admin: appeals, audit --------------------------------------------------------------------
export function useAdminAppeals(status: "open" | "accepted" | "rejected") {
  return useInfiniteQuery({
    queryKey: ["admin", "appeals", status],
    initialPageParam: undefined as string | undefined,
    queryFn: async ({ pageParam }) => {
      const { data, error } = await api.GET("/api/admin/appeals", {
        params: { query: { status, limit: 20, cursor: pageParam } },
      });
      if (!data) throw error;
      return data;
    },
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  });
}

export function useResolveAppeal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (v: { id: string; decision: "accept" | "reject"; response: string }) => {
      const { error } = await api.POST("/api/admin/appeals/{appeal_id}/resolve", {
        params: { path: { appeal_id: v.id } },
        body: { decision: v.decision, response: v.response },
      });
      if (error) fail(error);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin"] }),
  });
}

export function useAuditLog(filters: AuditFilters) {
  return useInfiniteQuery({
    queryKey: ["admin", "audit", filters],
    initialPageParam: undefined as string | undefined,
    queryFn: async ({ pageParam }) => {
      const { data, error } = await api.GET("/api/admin/audit", {
        params: { query: { ...filters, limit: 30, cursor: pageParam } },
      });
      if (!data) throw error;
      return data;
    },
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  });
}

// --- the signed-in user's own history and appeals -------------------------------------------------
export function useMyModeration() {
  const { status } = useSession();
  return useInfiniteQuery({
    queryKey: ["my-moderation"],
    enabled: status === "authenticated",
    initialPageParam: undefined as string | undefined,
    queryFn: async ({ pageParam }) => {
      const { data, error } = await api.GET("/api/me/moderation", {
        params: { query: { limit: 20, cursor: pageParam } },
      });
      if (!data) throw error;
      return data;
    },
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  });
}

export function useMyAppeals() {
  const { status } = useSession();
  return useQuery({
    queryKey: ["my-appeals"],
    enabled: status === "authenticated",
    queryFn: async () => {
      const { data, error } = await api.GET("/api/me/appeals", {
        params: { query: { limit: 50 } },
      });
      if (!data) throw error;
      return data.items;
    },
  });
}

export function useAppealContent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (v: { itemId: string; message: string }) => {
      const { error } = await api.POST("/api/content/{item_id}/appeal", {
        params: { path: { item_id: v.itemId } },
        body: { message: v.message },
      });
      if (error) fail(error);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["my-appeals"] }),
  });
}
