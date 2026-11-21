"use client";

import { useEffect } from "react";
import { api } from "@/lib/api/client";

/** A best-effort, deduplicated view receipt; the API stores no visitor IP. */
export function ViewTracker({ itemId, published }: { itemId: string; published: boolean }) {
  useEffect(() => {
    if (!published) return;
    void api
      .POST("/api/content/{item_id}/view", { params: { path: { item_id: itemId } } })
      .catch(() => {});
  }, [itemId, published]);
  return null;
}
