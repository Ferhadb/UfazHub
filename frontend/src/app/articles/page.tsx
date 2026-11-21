import type { Metadata } from "next";
import { Suspense } from "react";
import { ArticlesView } from "@/components/articles/articles-view";

export const metadata: Metadata = { title: "Articles" };

export default function Page() {
  return (
    <Suspense>
      <ArticlesView />
    </Suspense>
  );
}
