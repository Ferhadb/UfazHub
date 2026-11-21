"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "@/lib/auth/use-session";
import { api, errorInfo } from "./client";
import type { components } from "./schema";

export type ReadingList = components["schemas"]["ReadingListOut"];
export type SharedList = components["schemas"]["SharedList"];

const KEY = ["reading-lists"];
const fail = (error: unknown) => new Error(errorInfo(error).message);

export function useReadingLists() {
  const { status } = useSession();
  return useQuery({
    queryKey: KEY,
    enabled: status === "authenticated",
    queryFn: async () => {
      const { data, error } = await api.GET("/api/me/reading-lists");
      if (!data) throw error;
      return data.items;
    },
  });
}

/** Every list mutation refreshes the lists and whichever card caches they feed. */
export function useListActions() {
  const qc = useQueryClient();
  const done = () => {
    void qc.invalidateQueries({ queryKey: KEY });
    void qc.invalidateQueries({ queryKey: ["cards", "list"] });
  };
  const create = useMutation({
    mutationFn: async (name: string) => {
      const { data, error } = await api.POST("/api/me/reading-lists", { body: { name } });
      if (!data) throw fail(error);
      return data;
    },
    onSuccess: done,
  });
  const rename = useMutation({
    mutationFn: async (v: { id: string; name: string }) => {
      const { data, error } = await api.PATCH("/api/reading-lists/{list_id}", {
        params: { path: { list_id: v.id } },
        body: { name: v.name },
      });
      if (!data) throw fail(error);
    },
    onSuccess: done,
  });
  const remove = useMutation({
    mutationFn: async (id: string) => {
      const { response, error } = await api.DELETE("/api/reading-lists/{list_id}", {
        params: { path: { list_id: id } },
      });
      if (!response.ok) throw fail(error);
    },
    onSuccess: done,
  });
  const addItem = useMutation({
    mutationFn: async (v: { id: string; itemId: string }) => {
      const { data, error } = await api.PUT("/api/reading-lists/{list_id}/items/{item_id}", {
        params: { path: { list_id: v.id, item_id: v.itemId } },
      });
      if (!data) throw fail(error);
    },
    onSuccess: done,
  });
  const removeItem = useMutation({
    mutationFn: async (v: { id: string; itemId: string }) => {
      const { data, error } = await api.DELETE("/api/reading-lists/{list_id}/items/{item_id}", {
        params: { path: { list_id: v.id, item_id: v.itemId } },
      });
      if (!data) throw fail(error);
    },
    onSuccess: done,
  });
  const share = useMutation({
    mutationFn: async (v: { id: string; on: boolean }) => {
      const params = { params: { path: { list_id: v.id } } };
      const { data, error } = v.on
        ? await api.PUT("/api/reading-lists/{list_id}/share", params)
        : await api.DELETE("/api/reading-lists/{list_id}/share", params);
      if (!data) throw fail(error);
    },
    onSuccess: done,
  });
  return { create, rename, remove, addItem, removeItem, share };
}

export function useSharedList(token: string) {
  return useQuery({
    queryKey: ["shared-list", token],
    retry: false,
    queryFn: async () => {
      const { data, response } = await api.GET("/api/shared/lists/{token}", {
        params: { path: { token } },
      });
      if (!data)
        throw Object.assign(new Error("Could not load this list."), { status: response.status });
      return data;
    },
  });
}

export function useFollowTag() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (v: { slug: string; on: boolean }) => {
      const params = { params: { path: { slug: v.slug } } };
      const { data, error } = v.on
        ? await api.PUT("/api/tags/{slug}/follow", params)
        : await api.DELETE("/api/tags/{slug}/follow", params);
      if (!data) throw fail(error);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["followed-tags"] });
      void qc.invalidateQueries({ queryKey: ["cards", "for-you"] });
    },
  });
}

export function useReportBroken() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (linkId: string) => {
      const { data, error } = await api.PUT("/api/links/{link_id}/broken", {
        params: { path: { link_id: linkId } },
      });
      if (!data) throw fail(error);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["resource"] }),
  });
}
