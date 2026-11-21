"use client";

import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { useSession } from "@/lib/auth/use-session";
import { api } from "./client";
import type { components } from "./schema";

export type ItemCard = components["schemas"]["ItemCard"];
export type CardType = ItemCard["type"];
type CardPage = components["schemas"]["Page_ItemCard_"];

/** One hook for every list of catalogue cards: pass the key and a fetcher for a page. */
export function useCards(
  key: unknown[],
  fetchPage: (cursor: string | undefined) => Promise<CardPage | undefined>,
  enabled = true,
) {
  return useInfiniteQuery({
    queryKey: key,
    enabled,
    initialPageParam: undefined as string | undefined,
    queryFn: async ({ pageParam }) => {
      const data = await fetchPage(pageParam);
      if (!data) throw new Error("Could not load this list. Try again.");
      return data;
    },
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  });
}

export const useResearch = (type?: CardType) =>
  useCards(["cards", "research", type], async (cursor) => {
    const { data } = await api.GET("/api/research", {
      params: { query: { type, cursor, limit: 12 } },
    });
    return data;
  });

export const useForYou = () => {
  const { status } = useSession();
  return useCards(
    ["cards", "for-you"],
    async (cursor) => {
      const { data } = await api.GET("/api/feed/for-you", {
        params: { query: { cursor, limit: 12 } },
      });
      return data;
    },
    status === "authenticated",
  );
};

export const useBookmarks = () => {
  const { status } = useSession();
  return useCards(
    ["cards", "bookmarks"],
    async (cursor) => {
      const { data } = await api.GET("/api/me/bookmarks", {
        params: { query: { cursor, limit: 12 } },
      });
      return data;
    },
    status === "authenticated",
  );
};

export const useCourseItems = (slug: string, type?: CardType) =>
  useCards(["cards", "course", slug, type], async (cursor) => {
    const { data } = await api.GET("/api/courses/{slug}/items", {
      params: { path: { slug }, query: { type, cursor, limit: 12 } },
    });
    return data;
  });

export const useContributions = (id: string) =>
  useCards(["cards", "contributions", id], async (cursor) => {
    const { data } = await api.GET("/api/people/{user_id}/contributions", {
      params: { path: { user_id: id }, query: { cursor, limit: 12 } },
    });
    return data;
  });

export const useListItems = (listId: string) =>
  useCards(["cards", "list", listId], async (cursor) => {
    const { data } = await api.GET("/api/reading-lists/{list_id}/items", {
      params: { path: { list_id: listId }, query: { cursor, limit: 12 } },
    });
    return data;
  });

export function useFollowedTags() {
  const { status } = useSession();
  return useQuery({
    queryKey: ["followed-tags"],
    enabled: status === "authenticated",
    queryFn: async () => {
      const { data, error } = await api.GET("/api/me/tags");
      if (!data) throw error;
      return data;
    },
  });
}
