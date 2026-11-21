"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, errorInfo } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type SearchHit = components["schemas"]["SearchHit"];
export type SearchType = SearchHit["type"] | "all";

export function useDebounced<T>(value: T, ms = 200): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

export function useSearch(q: string, type: SearchType) {
  return useQuery({
    queryKey: ["search", q, type],
    enabled: q.length >= 2,
    staleTime: 30_000,
    retry: false,
    placeholderData: keepPreviousData,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/search", {
        params: { query: { q, type: type === "all" ? undefined : type, limit: 20 } },
      });
      if (!data) throw new Error(errorInfo(error).message);
      return data.items;
    },
  });
}

export const hitHref = (h: SearchHit) => `/${h.type}s/${h.call_number}`;
