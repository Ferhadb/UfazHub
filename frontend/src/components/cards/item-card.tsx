"use client";

import type { InfiniteData, UseInfiniteQueryResult } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { NameFx } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { Card } from "@/components/ui/card";
import type { Tint } from "@/components/ui/cn";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { ItemCard } from "@/lib/api/cards";
import { errorInfo } from "@/lib/api/client";

const SECTION = {
  resource: "resources",
  article: "articles",
  collection: "collections",
  question: "questions",
} as const;

export const itemHref = (c: Pick<ItemCard, "type" | "call_number">) =>
  `/${SECTION[c.type]}/${c.call_number}`;

/** A catalogue card for any content type; research items take the forest-green edge. */
export function ItemCardView({
  item,
  footer,
  tilt,
}: {
  item: ItemCard;
  footer?: ReactNode;
  tilt?: number;
}) {
  const tint: Tint = item.is_research ? "research" : item.type;
  return (
    <Card
      callNumber={item.call_number}
      tint={tint}
      title={item.title}
      href={itemHref(item)}
      tilt={tilt}
    >
      <p className="line-clamp-3">{item.description}</p>
      <p className="mt-3 flex flex-wrap items-center gap-2">
        <Badge tone={item.type}>{item.type}</Badge>
        {item.is_research && <Badge tone="research">research</Badge>}
        <span className="text-step--1 font-mono tabular-nums">
          {item.vote_score} votes ·{" "}
          <NameFx name={item.author.display_name} cosmetics={item.author.cosmetics} />
        </span>
      </p>
      {item.tags.length > 0 && (
        <p className="text-step--1 mt-2">
          {item.tags
            .slice(0, 4)
            .map((t) => `#${t}`)
            .join("  ")}
        </p>
      )}
      {footer && <div className="relative mt-3">{footer}</div>}
    </Card>
  );
}

/** Loading, error (with retry), empty and load-more around any infinite list of cards. */
export function CardList({
  query,
  empty,
  errorTitle = "The drawer is stuck",
  renderFooter,
}: {
  query: UseInfiniteQueryResult<InfiniteData<{ items: ItemCard[]; next_cursor?: string | null }>>;
  empty: ReactNode;
  errorTitle?: string;
  renderFooter?: (item: ItemCard) => ReactNode;
}) {
  const items = query.data?.pages.flatMap((p) => p.items) ?? [];
  return (
    <div aria-live="polite">
      {query.isPending ? (
        <Skeleton lines={4} />
      ) : query.isError ? (
        <Callout tone="danger" title={errorTitle}>
          <p>{errorInfo(query.error).message}</p>
          <Button className="mt-3" variant="secondary" onClick={() => query.refetch()}>
            Try again
          </Button>
        </Callout>
      ) : items.length === 0 ? (
        empty
      ) : (
        <ul className="grid gap-6 sm:grid-cols-2">
          {items.map((i, n) => (
            <li key={i.id}>
              <ItemCardView item={i} tilt={n % 2 ? 0.6 : -0.6} footer={renderFooter?.(i)} />
            </li>
          ))}
        </ul>
      )}
      {query.hasNextPage && (
        <div className="mt-8 flex justify-center">
          <Button
            variant="secondary"
            loading={query.isFetchingNextPage}
            onClick={() => query.fetchNextPage()}
          >
            Load more
          </Button>
        </div>
      )}
    </div>
  );
}

export const NothingYet = ({
  title = "Nothing here yet",
  children = "Be the first to leave a footprint.",
}: {
  title?: string;
  children?: ReactNode;
}) => <EmptyState title={title}>{children}</EmptyState>;
