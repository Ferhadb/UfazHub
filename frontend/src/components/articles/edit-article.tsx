"use client";

import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useArticle } from "@/lib/api/library";
import { useSession } from "@/lib/auth/use-session";
import { ArticleForm } from "./article-form";

export function EditArticle({ refId }: { refId: string }) {
  const { user } = useSession();
  const q = useArticle(refId);
  return (
    <main id="main" className="relative z-10 mx-auto max-w-2xl px-4 py-8 sm:py-12">
      <h1 className="font-display text-step-4">Edit article</h1>
      {q.isPending ? (
        <Skeleton lines={6} />
      ) : q.isError ? (
        <EmptyState title="Could not open that article">{q.error.message}</EmptyState>
      ) : user && (user.id === q.data.author.id || user.role === "admin") ? (
        <ArticleForm article={q.data} />
      ) : (
        <EmptyState title="Not yours to edit">
          Only the author or a moderator can edit this.
        </EmptyState>
      )}
    </main>
  );
}
