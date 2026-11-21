"use client";

import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, errorInfo } from "./client";
import type { components, operations } from "./schema";

export type Question = components["schemas"]["QuestionOut"];
export type Answer = components["schemas"]["AnswerOut"];
export type SimilarHit = components["schemas"]["SimilarHit"];
export type QuestionFilters = NonNullable<
  operations["list_questions_api_questions_get"]["parameters"]["query"]
>;

export function useQuestions(filters: QuestionFilters) {
  return useInfiniteQuery({
    queryKey: ["questions", filters],
    initialPageParam: undefined as string | undefined,
    queryFn: async ({ pageParam }) => {
      const { data, error } = await api.GET("/api/questions", {
        params: { query: { ...filters, limit: 12, cursor: pageParam } },
      });
      if (!data) throw error;
      return data;
    },
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  });
}

export function useQuestion(callNumber: string) {
  return useQuery({
    queryKey: ["question", callNumber],
    retry: false,
    queryFn: async () => {
      const { data, error, response } = await api.GET("/api/questions/{call_number}", {
        params: { path: { call_number: callNumber } },
      });
      if (!data)
        throw Object.assign(new Error(errorInfo(error).message), { status: response.status });
      return data;
    },
  });
}

export function useAnswers(callNumber: string) {
  return useInfiniteQuery({
    queryKey: ["answers", callNumber],
    initialPageParam: undefined as string | undefined,
    queryFn: async ({ pageParam }) => {
      const { data, error } = await api.GET("/api/questions/{call_number}/answers", {
        params: { path: { call_number: callNumber }, query: { limit: 20, cursor: pageParam } },
      });
      if (!data) throw error;
      return data;
    },
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  });
}

/** Questions that look like the title being typed. Advisory: a failure just shows nothing. */
export function useSimilar(title: string) {
  return useQuery({
    queryKey: ["similar", title],
    enabled: title.length >= 4,
    staleTime: 30_000,
    retry: false,
    queryFn: async () => {
      const { data } = await api.GET("/api/questions/similar", { params: { query: { title } } });
      return data ?? [];
    },
  });
}

/** Answering, accepting, pinning and merging; every one refreshes the thread from the server. */
export function useThreadActions(question: Question) {
  const qc = useQueryClient();
  const refresh = () => {
    void qc.invalidateQueries({ queryKey: ["answers", question.call_number] });
    void qc.invalidateQueries({ queryKey: ["question"] });
    void qc.invalidateQueries({ queryKey: ["questions"] });
  };
  const answer = useMutation({
    mutationFn: async (body: string) => {
      const { data, error } = await api.POST("/api/questions/{item_id}/answers", {
        params: { path: { item_id: question.id } },
        body: { body },
      });
      if (!data) throw error;
      return data;
    },
    onSuccess: refresh,
  });
  const accept = useMutation({
    mutationFn: async (v: { id: string; on: boolean }) => {
      const call = v.on ? api.PUT : api.DELETE;
      const { data, error } = await call("/api/answers/{answer_id}/accept", {
        params: { path: { answer_id: v.id } },
      });
      if (!data) throw error;
      return data;
    },
    onSuccess: refresh,
  });
  const pin = useMutation({
    mutationFn: async (v: { id: string; on: boolean }) => {
      const call = v.on ? api.PUT : api.DELETE;
      const { data, error } = await call("/api/answers/{answer_id}/pin", {
        params: { path: { answer_id: v.id } },
      });
      if (!data) throw error;
      return data;
    },
    onSuccess: refresh,
  });
  const merge = useMutation({
    mutationFn: async (of: string) => {
      const { error, response } = await api.PUT("/api/questions/{item_id}/duplicate", {
        params: { path: { item_id: question.id } },
        body: { of },
      });
      if (!response.ok) throw error;
    },
    onSuccess: refresh,
  });
  return { answer, accept, pin, merge };
}
