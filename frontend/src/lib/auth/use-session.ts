"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { readCsrfCookie, setAccessToken } from "./token";

export type User = components["schemas"]["UserOut"];
type Session = { user: User; refreshAt: number } | null;
const KEY = ["session"] as const;

const toSession = (t: components["schemas"]["TokenOut"]): Session => {
  setAccessToken(t.access_token);
  return { user: t.user, refreshAt: Date.now() + t.expires_in * 800 }; // refresh at 80% of lifetime
};

/** One refresh at a time across tabs: the cookie rotates, so a second tab must wait and reuse it. */
async function withLock<T>(fn: () => Promise<T>): Promise<T> {
  return navigator.locks ? navigator.locks.request("ufazhub-refresh", fn) : fn();
}

async function restore(): Promise<Session> {
  if (!readCsrfCookie()) return null; // never signed in on this browser: skip the doomed request
  const { data, response } = await withLock(() => api.POST("/api/auth/refresh"));
  if (data) return toSession(data);
  setAccessToken(null);
  if (response.status === 401 || response.status === 403) return null;
  throw new Error("Could not restore the session");
}

/** The single entry point for auth state. Pages never see tokens. */
export function useSession() {
  const qc = useQueryClient();
  const query = useQuery({
    queryKey: KEY,
    queryFn: restore,
    retry: false,
    staleTime: 5 * 60_000,
    refetchOnWindowFocus: true,
    refetchInterval: (q) =>
      q.state.data ? Math.max(q.state.data.refreshAt - Date.now(), 30_000) : false,
  });

  const login = useMutation({
    mutationFn: async (body: { email: string; password: string }) => {
      const { data, error } = await api.POST("/api/auth/login", { body });
      if (!data) throw error;
      return toSession(data);
    },
    onSuccess: (s) => qc.setQueryData(KEY, s),
  });

  const end = (path: "/api/auth/logout" | "/api/auth/logout-all") => async () => {
    await api.POST(path);
    setAccessToken(null);
    qc.setQueryData(KEY, null);
    qc.removeQueries({ predicate: (q) => q.queryKey[0] !== "session" });
  };
  const logout = useMutation({ mutationFn: end("/api/auth/logout") });
  const logoutAll = useMutation({ mutationFn: end("/api/auth/logout-all") });

  const user = query.data?.user ?? null;
  return {
    user,
    status: query.isPending
      ? ("loading" as const)
      : user
        ? ("authenticated" as const)
        : ("anonymous" as const),
    login: login.mutateAsync,
    logout: logout.mutateAsync,
    logoutAll: logoutAll.mutateAsync,
  };
}
