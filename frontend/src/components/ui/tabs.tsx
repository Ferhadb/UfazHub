"use client";

import * as T from "@radix-ui/react-tabs";
import type { ComponentProps } from "react";
import { cn, type Tint } from "./cn";

// Literal class names (Tailwind scans source text; built strings would be missed).
const active: Record<Tint, string> = {
  resource: "data-[state=active]:border-t-resource data-[state=active]:text-resource",
  article: "data-[state=active]:border-t-article data-[state=active]:text-article",
  collection: "data-[state=active]:border-t-collection data-[state=active]:text-collection",
  question: "data-[state=active]:border-t-question data-[state=active]:text-question",
  research: "data-[state=active]:border-t-research data-[state=active]:text-research",
};

export const Tabs = T.Root;

export const TabsList = ({ className, ...rest }: ComponentProps<typeof T.List>) => (
  <T.List
    className={cn("border-rule flex gap-1 overflow-x-auto border-b-2", className)}
    {...rest}
  />
);

/** Index-card tab: the active tab is a raised card with a coloured top edge. */
export function TabsTrigger({
  tint = "resource",
  className,
  ...rest
}: { tint?: Tint } & ComponentProps<typeof T.Trigger>) {
  return (
    <T.Trigger
      className={cn(
        "text-step-0 text-muted min-h-11 shrink-0 rounded-t-md border-t-4 border-transparent px-4 font-semibold",
        "data-[state=active]:bg-card data-[state=active]:shadow-paper data-[state=active]:-mb-0.5 data-[state=active]:rounded-b-none",
        "hover:text-ink",
        active[tint],
        className,
      )}
      {...rest}
    />
  );
}

export const TabsContent = ({ className, ...rest }: ComponentProps<typeof T.Content>) => (
  <T.Content className={cn("bg-card shadow-paper rounded-b-md p-4", className)} {...rest} />
);
