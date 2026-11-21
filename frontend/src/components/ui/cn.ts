import { clsx, type ClassValue } from "clsx";

export const cn = (...inputs: ClassValue[]) => clsx(inputs);

export type Tint = "resource" | "article" | "collection" | "question" | "research";

// Full class names so Tailwind can see them.
export const tintText: Record<Tint, string> = {
  resource: "text-resource",
  article: "text-article",
  collection: "text-collection",
  question: "text-question",
  research: "text-research",
};
export const tintTop: Record<Tint, string> = {
  resource: "border-t-resource",
  article: "border-t-article",
  collection: "border-t-collection",
  question: "border-t-question",
  research: "border-t-research",
};
export const tintBorder: Record<Tint, string> = {
  resource: "border-resource",
  article: "border-article",
  collection: "border-collection",
  question: "border-question",
  research: "border-research",
};
