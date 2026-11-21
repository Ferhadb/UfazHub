"use client";

import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, errorInfo } from "./client";
import type { components } from "./schema";
import { useSession } from "@/lib/auth/use-session";

export type Notification = components["schemas"]["NotificationOut"];
export type ReputationRules = components["schemas"]["ReputationRules"];

export function useUnreadCount() {
  const { status } = useSession();
  return useQuery({
    queryKey: ["notifications-unread"],
    enabled: status === "authenticated",
    refetchInterval: 60_000,
    retry: false,
    queryFn: async () => {
      const { data } = await api.GET("/api/notifications/unread");
      return data?.unread ?? 0;
    },
  });
}

export function useNotifications(unreadOnly: boolean) {
  return useInfiniteQuery({
    queryKey: ["notifications", unreadOnly],
    initialPageParam: undefined as string | undefined,
    queryFn: async ({ pageParam }) => {
      const { data, error } = await api.GET("/api/notifications", {
        params: { query: { unread: unreadOnly, limit: 20, cursor: pageParam } },
      });
      if (!data) throw error;
      return data;
    },
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  });
}

/** Mark some (or, with no ids, all) notifications read. */
export function useMarkRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (ids?: string[]) => {
      const { data, error } = await api.POST("/api/notifications/read", {
        body: { ids: ids ?? null },
      });
      if (!data) throw new Error(errorInfo(error).message);
      return data;
    },
    onSuccess: (data) => {
      qc.setQueryData(["notifications-unread"], data.unread);
      void qc.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}

export function useDigestSetting() {
  const qc = useQueryClient();
  const query = useQuery({
    queryKey: ["notification-settings"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/notifications/settings");
      if (!data) throw error;
      return data;
    },
  });
  const set = useMutation({
    mutationFn: async (email_digest: boolean) => {
      const { data, error } = await api.PUT("/api/notifications/settings", {
        body: { email_digest },
      });
      if (!data) throw new Error(errorInfo(error).message);
      return data;
    },
    onSuccess: (d) => qc.setQueryData(["notification-settings"], d),
  });
  return { query, set };
}

export function useReputationRules() {
  return useQuery({
    queryKey: ["reputation-rules"],
    staleTime: 10 * 60_000,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/reputation/rules");
      if (!data) throw error;
      return data;
    },
  });
}

export function useMyReputation() {
  const { status } = useSession();
  return useInfiniteQuery({
    queryKey: ["my-reputation"],
    enabled: status === "authenticated",
    initialPageParam: undefined as string | undefined,
    queryFn: async ({ pageParam }) => {
      const { data, error } = await api.GET("/api/me/reputation", {
        params: { query: { limit: 20, cursor: pageParam } },
      });
      if (!data) throw error;
      return data;
    },
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  });
}
