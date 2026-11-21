"use client";

import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query";
import { usePathname, useRouter } from "next/navigation";
import { useToast } from "@/components/ui/toast";
import { useSession } from "@/lib/auth/use-session";
import { api, errorInfo } from "./client";
import type { components, operations } from "./schema";

export type Resource = components["schemas"]["ResourceOut"];
export type ResourcePage = components["schemas"]["Page_ResourceOut_"];
export type Difficulty = components["schemas"]["ResourceIn"]["difficulty"];
export type ResourceFilters = NonNullable<
  operations["list_resources_api_resources_get"]["parameters"]["query"]
>;

const RESOURCES = "resources"; // infinite lists
const RESOURCE = "resource"; // single detail
/** Every cache that can hold a votable item: lists ("...s") and details of each content type. */
const CONTENT_KEYS = [RESOURCES, RESOURCE, "articles", "article", "collections", "collection"];

/** The fields votes and bookmarks touch; resources, articles and collections all have them. */
export type Votable = Pick<
  Resource,
  "id" | "my_vote" | "vote_score" | "bookmarked" | "bookmark_count"
>;

export function useResources(filters: ResourceFilters) {
  return useInfiniteQuery({
    queryKey: [RESOURCES, filters],
    initialPageParam: undefined as string | undefined,
    queryFn: async ({ pageParam }) => {
      const { data, error } = await api.GET("/api/resources", {
        params: { query: { ...filters, limit: 12, cursor: pageParam } },
      });
      if (!data) throw error;
      return data;
    },
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  });
}

export function useResource(callNumber: string) {
  return useQuery({
    queryKey: [RESOURCE, callNumber],
    retry: false,
    queryFn: async () => {
      const { data, error, response } = await api.GET("/api/resources/{call_number}", {
        params: { path: { call_number: callNumber } },
      });
      if (!data)
        throw Object.assign(new Error(errorInfo(error).message), { status: response.status });
      return data;
    },
  });
}

export function useTopTags(limit = 12) {
  return useQuery({
    queryKey: ["tags", limit],
    staleTime: 5 * 60_000,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/tags", { params: { query: { limit } } });
      if (!data) throw error;
      return data.items;
    },
  });
}

type Snapshot = [readonly unknown[], unknown][];

/** Apply `fn` to one item everywhere it is cached (every list and its detail page). */
function patchItem(qc: QueryClient, id: string, fn: <T extends Votable>(r: T) => T) {
  for (const key of CONTENT_KEYS) {
    qc.setQueriesData({ queryKey: [key] }, (d: unknown) => {
      const data = d as { pages?: { items: Votable[] }[]; id?: string } | undefined;
      if (data?.pages)
        return {
          ...data,
          pages: data.pages.map((p) => ({
            ...p,
            items: p.items.map((r) => (r.id === id ? fn(r) : r)),
          })),
        };
      return data?.id === id ? fn(data as Votable) : d;
    });
  }
}

const snapshot = (qc: QueryClient): Snapshot =>
  CONTENT_KEYS.flatMap((key) => qc.getQueriesData({ queryKey: [key] }));

/** Sign-in gate for guests: sends them to sign in and brings them back. */
function useGuard() {
  const { status } = useSession();
  const router = useRouter();
  const pathname = usePathname();
  const toast = useToast();
  return (): boolean => {
    if (status === "authenticated") return true;
    toast({ title: "Sign in to continue", description: "Votes and bookmarks need an account." });
    router.push(`/signin?next=${encodeURIComponent(pathname)}`);
    return false;
  };
}

/** Optimistic votes and bookmarks: the UI moves first, the server's numbers win, errors roll back. */
export function useResourceActions(resource: Votable) {
  const qc = useQueryClient();
  const toast = useToast();
  const guard = useGuard();
  const id = resource.id;

  const rollback = (snap: Snapshot | undefined, error: unknown) => {
    snap?.forEach(([key, data]) => qc.setQueryData(key, data));
    toast({
      title: "That did not go through",
      description: errorInfo(error).message,
      tone: "danger",
    });
  };

  const voteMutation = useMutation({
    mutationFn: async (value: -1 | 0 | 1) => {
      const { data, error } = await api.PUT("/api/content/{item_id}/vote", {
        params: { path: { item_id: id } },
        body: { value },
      });
      if (!data) throw error;
      return data;
    },
    onMutate: async (value) => {
      await Promise.all(CONTENT_KEYS.map((key) => qc.cancelQueries({ queryKey: [key] })));
      const snap = snapshot(qc);
      patchItem(qc, id, (r) => ({
        ...r,
        my_vote: value,
        vote_score: r.vote_score + value - r.my_vote,
      }));
      return snap;
    },
    onError: (e, _v, snap) => rollback(snap, e),
    onSuccess: (data) =>
      patchItem(qc, id, (r) => ({ ...r, vote_score: data.vote_score, my_vote: data.my_vote })),
  });

  const bookmarkMutation = useMutation({
    mutationFn: async (on: boolean) => {
      const call = on ? api.PUT : api.DELETE;
      const { data, error } = await call("/api/content/{item_id}/bookmark", {
        params: { path: { item_id: id } },
      });
      if (!data) throw error;
      return data;
    },
    onMutate: async (on) => {
      await Promise.all(CONTENT_KEYS.map((key) => qc.cancelQueries({ queryKey: [key] })));
      const snap = snapshot(qc);
      patchItem(qc, id, (r) => ({
        ...r,
        bookmarked: on,
        bookmark_count: r.bookmark_count + (on ? 1 : -1),
      }));
      return snap;
    },
    onError: (e, _v, snap) => rollback(snap, e),
    onSuccess: (data) =>
      patchItem(qc, id, (r) => ({
        ...r,
        bookmarked: data.bookmarked,
        bookmark_count: data.bookmark_count,
      })),
  });

  return {
    /** Clicking the arrow you already chose takes the vote back. */
    vote: (dir: 1 | -1) => {
      if (guard()) voteMutation.mutate(resource.my_vote === dir ? 0 : dir);
    },
    toggleBookmark: () => {
      if (guard()) bookmarkMutation.mutate(!resource.bookmarked);
    },
  };
}
