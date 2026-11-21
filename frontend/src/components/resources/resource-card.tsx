import Link from "next/link";
import { Badge, Stamp } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import type { Resource } from "@/lib/api/content";
import { ResourceActions } from "./actions";

export const formatMinutes = (m: number | null | undefined) =>
  m == null ? null : m < 60 ? `${m} min` : `${Math.round((m / 60) * 10) / 10} h`;

export function ResourceCard({ resource: r, tilt }: { resource: Resource; tilt?: number }) {
  const time = formatMinutes(r.time_commitment_minutes);
  return (
    <Card
      callNumber={r.call_number}
      tint={r.is_research ? "research" : "resource"}
      title={r.title}
      href={`/resources/${r.call_number}`}
      tilt={tilt}
      stamp={r.status === "pending_review" ? <Stamp tone="flame">In review</Stamp> : undefined}
    >
      <p className="line-clamp-3">{r.description}</p>
      <p className="mt-3 flex flex-wrap gap-2">
        <Badge tone="resource">{r.resource_type}</Badge>
        <Badge>{r.difficulty}</Badge>
        {time && <Badge>{time}</Badge>}
        {r.is_research && <Badge tone="research">research</Badge>}
      </p>
      {r.tags.length > 0 && (
        <ul aria-label="Tags" className="text-step--1 relative mt-3 flex flex-wrap gap-x-3">
          {r.tags.slice(0, 4).map((t) => (
            <li key={t}>
              <Link
                href={`/resources?tag=${encodeURIComponent(slug(t))}`}
                className="inline-flex min-h-11 items-center underline-offset-4 hover:underline"
              >
                #{t}
              </Link>
            </li>
          ))}
        </ul>
      )}
      <ResourceActions resource={r} className="mt-1" />
    </Card>
  );
}

/** Mirrors the server's slug rule closely enough for filter links (lower-case, dashes). */
export const slug = (t: string) =>
  t
    .normalize("NFKC")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, "-")
    .replace(/^-|-$/g, "");
