"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Button, buttonClass } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { EmptyState } from "@/components/ui/empty-state";
import { Select } from "@/components/ui/field";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/toggles";
import { errorInfo } from "@/lib/api/client";
import { useArticles } from "@/lib/api/library";
import { ArticleCard } from "./article-card";

export function ArticlesView() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const filters = {
    sort: params.get("sort") === "top" ? ("top" as const) : ("latest" as const),
    tag: params.get("tag") || undefined,
    research: params.get("research") === "1" ? true : undefined,
  };
  const set = (patch: Record<string, string | null>) => {
    const next = new URLSearchParams(params.toString());
    for (const [k, v] of Object.entries(patch)) {
      if (v) next.set(k, v);
      else next.delete(k);
    }
    router.replace(`${pathname}${next.size ? `?${next}` : ""}`, { scroll: false });
  };
  const q = useArticles(filters);
  const items = q.data?.pages.flatMap((p) => p.items) ?? [];
  const filtered = Boolean(filters.tag || filters.research);

  return (
    <main id="main" className="relative z-10 mx-auto max-w-5xl px-4 py-8 sm:px-8 sm:py-12">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-step--1 text-article font-mono tracking-widest uppercase">
            Catalogue · Articles
          </p>
          <h1 className="font-display text-step-4 mt-1">Articles</h1>
        </div>
        <Link href="/submit?type=article" className={buttonClass("primary")}>
          Write an article
        </Link>
      </div>
      <section aria-label="Filters" className="mt-8 flex flex-wrap items-end gap-x-6 gap-y-3">
        <Select
          label="Order"
          value={filters.sort}
          onChange={(e) => set({ sort: e.target.value === "top" ? "top" : null })}
        >
          <option value="latest">Newest</option>
          <option value="top">Most upvoted</option>
        </Select>
        <Switch
          label="Research only"
          checked={Boolean(filters.research)}
          onCheckedChange={(on) => set({ research: on ? "1" : null })}
        />
        {filters.tag && (
          <Button variant="secondary" onClick={() => set({ tag: null })}>
            #{filters.tag} · clear
          </Button>
        )}
      </section>
      <div className="mt-6" aria-live="polite">
        {q.isPending ? (
          <div className="grid gap-6 sm:grid-cols-2">
            {Array.from({ length: 4 }, (_, i) => (
              <Skeleton key={i} />
            ))}
          </div>
        ) : q.isError ? (
          <Callout tone="danger" title="The drawer is stuck">
            <p>{errorInfo(q.error).message}</p>
            <Button className="mt-3" variant="secondary" onClick={() => q.refetch()}>
              Try again
            </Button>
          </Callout>
        ) : items.length === 0 ? (
          <EmptyState
            title={filtered ? "No article matches that" : "Nothing here yet"}
            action={
              filtered ? (
                <Button variant="secondary" onClick={() => router.replace(pathname)}>
                  Clear filters
                </Button>
              ) : (
                <Link href="/submit?type=article" className={buttonClass("primary")}>
                  Write the first one
                </Link>
              )
            }
          >
            {filtered
              ? "Loosen a filter and the pages will fill back up."
              : "Be the first to write one."}
          </EmptyState>
        ) : (
          <ul className="grid gap-6 sm:grid-cols-2">
            {items.map((a, i) => (
              <li key={a.id}>
                <ArticleCard article={a} tilt={i % 2 ? 0.6 : -0.6} />
              </li>
            ))}
          </ul>
        )}
        {q.hasNextPage && (
          <div className="mt-8 flex justify-center">
            <Button
              variant="secondary"
              loading={q.isFetchingNextPage}
              onClick={() => q.fetchNextPage()}
            >
              Load more
            </Button>
          </div>
        )}
      </div>
    </main>
  );
}
