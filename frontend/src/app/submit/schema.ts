import { z } from "zod";

export const RESOURCE_TYPES = [
  "book",
  "video",
  "course",
  "article",
  "paper",
  "notes",
  "exam",
  "tool",
  "dataset",
  "other",
] as const;
export const DIFFICULTIES = ["beginner", "intermediate", "advanced"] as const;

const http = (v: string) => {
  try {
    const u = new URL(v);
    return (u.protocol === "http:" || u.protocol === "https:") && !u.username && !u.password;
  } catch {
    return false;
  }
};

// Mirrors the API's limits; the server stays the authority (its field errors are shown too).
export const submitSchema = z.object({
  title: z.string().trim().min(3, "At least 3 characters").max(200, "At most 200 characters"),
  description: z
    .string()
    .trim()
    .min(10, "Say a little more (10 characters or more)")
    .max(2000, "At most 2000 characters"),
  resource_type: z.enum(RESOURCE_TYPES),
  difficulty: z.enum(DIFFICULTIES),
  category: z.string().trim().max(60, "At most 60 characters"),
  minutes: z.string().regex(/^\d{0,6}$/, "Whole minutes, for example 90"),
  prerequisites: z.string().max(2000),
  best_part: z.string().max(2000),
  warning: z.string().max(2000),
  student_note: z.string().max(2000),
  tags: z
    .string()
    .refine((v) => v.split(",").filter((t) => t.trim()).length <= 8, "At most 8 tags"),
  is_research: z.boolean(),
  links: z
    .array(
      z.object({
        url: z.string().trim().max(2048).refine(http, "Enter a full http(s) link"),
        label: z.string().trim().max(120, "At most 120 characters"),
      }),
    )
    .min(1)
    .max(5),
});
export type SubmitValues = z.infer<typeof submitSchema>;
