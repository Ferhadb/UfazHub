"use client";

import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, errorInfo } from "./client";
import type { components, operations } from "./schema";

export type Person = components["schemas"]["PersonCard"];
export type Profile = components["schemas"]["Profile"];
export type LeaderRow = components["schemas"]["LeaderRow"];
export type ProfilePatch = components["schemas"]["ProfilePatch"];
export type PeopleFilters = NonNullable<
  operations["directory_api_people_get"]["parameters"]["query"]
>;

export function usePeople(filters: PeopleFilters) {
  return useInfiniteQuery({
    queryKey: ["people", filters],
    initialPageParam: undefined as string | undefined,
    queryFn: async ({ pageParam }) => {
      const { data, error } = await api.GET("/api/people", {
        params: { query: { ...filters, limit: 24, cursor: pageParam } },
      });
      if (!data) throw error;
      return data;
    },
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  });
}

export function usePerson(id: string) {
  return useQuery({
    queryKey: ["person", id],
    retry: false,
    queryFn: async () => {
      const { data, response } = await api.GET("/api/people/{user_id}", {
        params: { path: { user_id: id } },
      });
      if (!data)
        throw Object.assign(new Error("Could not load this profile."), { status: response.status });
      return data;
    },
  });
}

export function useLeaderboard(period: "month" | "all") {
  return useQuery({
    queryKey: ["leaderboard", period],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/leaderboard", {
        params: { query: { period, limit: 10 } },
      });
      if (!data) throw error;
      return data;
    },
  });
}

export function useContributorOfTheMonth() {
  return useQuery({
    queryKey: ["contributor-of-the-month"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/leaderboard/contributor-of-the-month");
      if (data === undefined) throw error;
      return data;
    },
  });
}

export function useUpdateProfile(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: ProfilePatch) => {
      const { data, error } = await api.PATCH("/api/me/profile", { body });
      if (!data) throw Object.assign(new Error(errorInfo(error).message), errorInfo(error));
      return data;
    },
    onSuccess: (data) => {
      qc.setQueryData(["person", id], data);
      void qc.invalidateQueries({ queryKey: ["people"] });
    },
  });
}

export function useRemoveAvatar(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { response, error } = await api.DELETE("/api/me/avatar");
      if (!response.ok) throw new Error(errorInfo(error).message);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["person", id] }),
  });
}
