"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { ResourceCard } from "@/components/resources/resource-card";
import { Shelf } from "@/components/resources/shelf";
import { Button, buttonClass } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { cn } from "@/components/ui/cn";
import { EmptyState } from "@/components/ui/empty-state";
import { Select } from "@/components/ui/field";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/toggles";
import { useResources, useTopTags, type Difficulty, type ResourceFilters } from "@/lib/api/content";
import { errorInfo } from "@/lib/api/client";

const VIEWS = ["list", "grid", "shelf"] as const;
type View = (typeof VIEWS)[number];
const DIFFICULTIES: Difficulty[] = ["beginner", "intermediate", "advanced"];

const layout: Record<Exclude<View, "shelf">, string> = {
  list: "flex flex-col gap-6",
  grid: "grid gap-6 sm:grid-cols-2 lg:grid-cols-3",
};

export function ResourcesView() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  const view = (VIEWS as readonly string[]).includes(params.get("view") ?? "")
    ? (params.get("view") as View)
    : "list";
  const filters: ResourceFilters = {
    sort: params.get("sort") === "top" ? "top" : "latest",
    tag: params.get("tag") || undefined,
    difficulty: DIFFICULTIES.find((d) => d === params.get("difficulty")),
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

  const q = useResources(filters);
  const tags = useTopTags();
  const items = q.data?.pages.flatMap((p) => p.items) ?? [];
  const filtered = Boolean(filters.tag || filters.difficulty || filters.research);

  return (
    <main id="main" className="relative z-10 mx-auto max-w-5xl px-4 py-8 sm:px-8 sm:py-12">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-step--1 text-resource font-mono tracking-widest uppercase">
            Catalogue · Resources
          </p>
          <h1 className="font-display text-step-4 mt-1">Resources</h1>
        </div>
        <Link href="/submit" className={buttonClass("primary")}>
          Submit a resource
        </Link>
      </div>

      <section aria-label="Filters" className="mt-8 flex flex-wrap items-end gap-x-6 gap-y-3">
        <Select
          label="Difficulty"
          value={filters.difficulty ?? ""}
          onChange={(e) => set({ difficulty: e.target.value || null })}
        >
          <option value="">Any</option>
          {DIFFICULTIES.map((d) => (
            <option key={d}>{d}</option>
          ))}
        </Select>
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
        <div role="group" aria-label="View" className="ml-auto flex gap-1">
          {VIEWS.map((v) => (
            <Button
              key={v}
              variant={v === view ? "primary" : "secondary"}
              aria-pressed={v === view}
              onClick={() => set({ view: v === "list" ? null : v })}
            >
              {v[0]!.toUpperCase() + v.slice(1)}
            </Button>
          ))}
        </div>
      </section>

      <div className="text-step--1 mt-4 flex flex-wrap items-center gap-x-3">
        {filters.tag && (
          <Button variant="secondary" onClick={() => set({ tag: null })}>
            #{filters.tag} · clear
          </Button>
        )}
        {!filters.tag && tags.data && tags.data.length > 0 && (
          <ul aria-label="Popular tags" className="flex flex-wrap gap-x-3">
            {tags.data.map((t) => (
              <li key={t.slug}>
                <button
                  type="button"
                  onClick={() => set({ tag: t.slug })}
                  className="min-h-11 underline-offset-4 hover:underline"
                >
                  #{t.name} <span className="text-muted font-mono">{t.count}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="mt-6" aria-live="polite">
        {q.isPending ? (
          <div className={cn(layout[view === "shelf" ? "grid" : view])}>
            {Array.from({ length: 6 }, (_, i) => (
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
            title={filtered ? "No card matches that" : "Nothing here yet"}
            action={
              filtered ? (
                <Button variant="secondary" onClick={() => router.replace(pathname)}>
                  Clear filters
                </Button>
              ) : (
                <Link href="/submit" className={buttonClass("primary")}>
                  Submit the first one
                </Link>
              )
            }
          >
            {filtered
              ? "Loosen a filter or two and the shelves will fill back up."
              : "Nothing here yet. Be the first to leave a footprint."}
          </EmptyState>
        ) : view === "shelf" ? (
          <Shelf resources={items} />
        ) : (
          <ul className={layout[view]}>
            {items.map((r, i) => (
              <li key={r.id}>
                <ResourceCard resource={r} tilt={i % 2 ? 0.6 : -0.6} />
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
