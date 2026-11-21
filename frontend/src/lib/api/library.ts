"use client";

import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, errorInfo } from "./client";
import type { components, operations } from "./schema";

export type Article = components["schemas"]["ArticleOut"];
export type ArticleCard = components["schemas"]["ArticleCard"];
export type Collection = components["schemas"]["CollectionOut"];
export type Comment = components["schemas"]["CommentOut"];
export type Attachment = components["schemas"]["AttachmentOut"];
export type ArticleFilters = NonNullable<
  operations["list_articles_api_articles_get"]["parameters"]["query"]
>;
export type CollectionFilters = NonNullable<
  operations["list_collections_api_collections_get"]["parameters"]["query"]
>;

/** A failed lookup that keeps its HTTP status so pages can tell "gone" from "broken". */
const failure = (error: unknown, status: number) =>
  Object.assign(new Error(errorInfo(error).message), { status });

export function useArticles(filters: ArticleFilters) {
  return useInfiniteQuery({
    queryKey: ["articles", filters],
    initialPageParam: undefined as string | undefined,
    queryFn: async ({ pageParam }) => {
      const { data, error } = await api.GET("/api/articles", {
        params: { query: { ...filters, limit: 12, cursor: pageParam } },
      });
      if (!data) throw error;
      return data;
    },
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  });
}

export function useArticle(ref: string) {
  return useQuery({
    queryKey: ["article", ref],
    retry: false,
    queryFn: async () => {
      const { data, error, response } = await api.GET("/api/articles/{ref}", {
        params: { path: { ref } },
      });
      if (!data) throw failure(error, response.status);
      return data;
    },
  });
}

export function useCollections(filters: CollectionFilters) {
  return useInfiniteQuery({
    queryKey: ["collections", filters],
    initialPageParam: undefined as string | undefined,
    queryFn: async ({ pageParam }) => {
      const { data, error } = await api.GET("/api/collections", {
        params: { query: { ...filters, limit: 24, cursor: pageParam } },
      });
      if (!data) throw error;
      return data;
    },
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  });
}

export function useCollection(callNumber: string) {
  return useQuery({
    queryKey: ["collection", callNumber],
    retry: false,
    queryFn: async () => {
      const { data, error, response } = await api.GET("/api/collections/{call_number}", {
        params: { path: { call_number: callNumber } },
      });
      if (!data) throw failure(error, response.status);
      return data;
    },
  });
}

export function useComments(itemId: string) {
  return useInfiniteQuery({
    queryKey: ["comments", itemId],
    initialPageParam: undefined as string | undefined,
    queryFn: async ({ pageParam }) => {
      const { data, error } = await api.GET("/api/content/{item_id}/comments", {
        params: { path: { item_id: itemId }, query: { limit: 20, cursor: pageParam } },
      });
      if (!data) throw error;
      return data;
    },
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  });
}

/** Post or delete a comment; the item's own counter is refreshed from the server afterwards. */
export function useCommentMutations(itemId: string) {
  const qc = useQueryClient();
  const refresh = () => {
    void qc.invalidateQueries({ queryKey: ["comments", itemId] });
    for (const key of ["resource", "article", "collection"])
      void qc.invalidateQueries({ queryKey: [key] });
  };
  const create = useMutation({
    mutationFn: async (v: { body: string; parent_id?: string }) => {
      const { data, error } = await api.POST("/api/content/{item_id}/comments", {
        params: { path: { item_id: itemId } },
        body: v,
      });
      if (!data) throw error;
      return data;
    },
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: async (id: string) => {
      const { error, response } = await api.DELETE("/api/comments/{comment_id}", {
        params: { path: { comment_id: id } },
      });
      if (!response.ok) throw error;
    },
    onSuccess: refresh,
  });
  return { create, remove };
}

/** Multipart upload through the typed client (the auth middleware adds the token). */
export async function uploadFile(file: File, purpose: "avatar" | "cover" | "attachment") {
  const { data, error } = await api.POST("/api/uploads", {
    // The generated type says `file: string` (a binary field); the serializer sends the real File.
    body: { file: file as unknown as string, purpose },
    bodySerializer: (b) => {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("purpose", (b as { purpose: string }).purpose);
      return fd;
    },
  });
  if (!data) throw new Error(errorInfo(error).message);
  return data;
}

export function useMarkdownPreview(markdown: string, enabled: boolean) {
  return useQuery({
    queryKey: ["md-preview", markdown],
    enabled,
    staleTime: Infinity,
    retry: false,
    queryFn: async () => {
      const { data, error } = await api.POST("/api/articles/preview", {
        body: { body_md: markdown },
      });
      if (!data) throw new Error(errorInfo(error).message);
      return data;
    },
  });
}
