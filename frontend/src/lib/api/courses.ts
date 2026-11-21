"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "./client";
import type { components } from "./schema";

export type Program = components["schemas"]["ProgramOut"];
export type Course = components["schemas"]["CourseOut"];
export type CourseDetail = components["schemas"]["CourseDetail"];

export function usePrograms() {
  return useQuery({
    queryKey: ["programs"],
    staleTime: 5 * 60_000,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/programs");
      if (!data) throw error;
      return data;
    },
  });
}

export function useCourse(slug: string) {
  return useQuery({
    queryKey: ["course", slug],
    retry: false,
    queryFn: async () => {
      const { data, response } = await api.GET("/api/courses/{slug}", {
        params: { path: { slug } },
      });
      if (!data)
        throw Object.assign(new Error("Could not load this course."), { status: response.status });
      return data;
    },
  });
}

export function useItemCourses(itemId: string) {
  return useQuery({
    queryKey: ["item-courses", itemId],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/content/{item_id}/courses", {
        params: { path: { item_id: itemId } },
      });
      if (!data) throw error;
      return data;
    },
  });
}
