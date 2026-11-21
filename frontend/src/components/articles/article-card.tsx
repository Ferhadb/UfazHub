import Link from "next/link";
import { ResourceActions } from "@/components/resources/actions";
import { slug } from "@/components/resources/resource-card";
import { Badge, Stamp } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import type { ArticleCard as Item } from "@/lib/api/library";

export function ArticleCard({ article: a, tilt }: { article: Item; tilt?: number }) {
  return (
    <Card
      callNumber={a.call_number}
      tint={a.is_research ? "research" : "article"}
      title={a.title}
      href={`/articles/${a.slug}`}
      tilt={tilt}
      stamp={
        a.status === "draft" ? (
          <Stamp tone="flame">Draft</Stamp>
        ) : a.status === "pending_review" ? (
          <Stamp tone="flame">In review</Stamp>
        ) : undefined
      }
    >
      <p className="line-clamp-3">{a.excerpt}</p>
      <p className="mt-3 flex flex-wrap gap-2">
        <Badge tone="article">{a.reading_minutes} min read</Badge>
        <Badge>{a.author.display_name}</Badge>
        {a.is_research && <Badge tone="research">research</Badge>}
      </p>
      {a.tags.length > 0 && (
        <ul aria-label="Tags" className="text-step--1 relative mt-3 flex flex-wrap gap-x-3">
          {a.tags.slice(0, 4).map((t) => (
            <li key={t}>
              <Link
                href={`/articles?tag=${encodeURIComponent(slug(t))}`}
                className="inline-flex min-h-11 items-center underline-offset-4 hover:underline"
              >
                #{t}
              </Link>
            </li>
          ))}
        </ul>
      )}
      <ResourceActions resource={a} className="mt-1" />
    </Card>
  );
}
