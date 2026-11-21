"use client";

import Link from "next/link";
import { Comments } from "@/components/comments/comments";
import { ResourceActions } from "@/components/resources/actions";
import { formatMinutes, slug } from "@/components/resources/resource-card";
import { Badge, Stamp } from "@/components/ui/badge";
import { Button, buttonClass } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { EmptyState } from "@/components/ui/empty-state";
import { Icon } from "@/components/ui/icons";
import { Marginalia } from "@/components/ui/marginalia";
import { Skeleton } from "@/components/ui/skeleton";
import { useResource } from "@/lib/api/content";

const Field = ({ label, children }: { label: string; children: string }) =>
  children ? (
    <div>
      <dt className="text-step--1 text-muted font-mono tracking-widest uppercase">{label}</dt>
      <dd className="mt-1 whitespace-pre-line">{children}</dd>
    </div>
  ) : null;

export function ResourceDetail({ callNumber }: { callNumber: string }) {
  const q = useResource(callNumber);

  if (q.isPending)
    return (
      <main id="main" className="relative z-10 mx-auto max-w-3xl px-4 py-10">
        <Skeleton lines={6} />
      </main>
    );
  if (q.isError) {
    const missing = (q.error as { status?: number }).status === 404;
    return (
      <main id="main" className="relative z-10 mx-auto max-w-3xl px-4 py-10">
        <EmptyState
          title={missing ? "No such card in the catalogue" : "The drawer is stuck"}
          action={
            missing ? (
              <Link href="/resources" className={buttonClass("secondary")}>
                Back to resources
              </Link>
            ) : (
              <Button variant="secondary" onClick={() => q.refetch()}>
                Try again
              </Button>
            )
          }
        >
          {missing ? "It may have been hidden, or it never existed." : q.error.message}
        </EmptyState>
      </main>
    );
  }

  const r = q.data;
  const time = formatMinutes(r.time_commitment_minutes);
  return (
    <main id="main" className="relative z-10 mx-auto max-w-5xl px-4 py-8 sm:px-8 sm:py-12 lg:pr-72">
      <Link
        href="/resources"
        className="text-step--1 inline-flex min-h-11 items-center gap-1 underline-offset-4 hover:underline"
      >
        <Icon name="chevron-left" size={16} /> All resources
      </Link>
      <article className="bg-card shadow-paper border-rule border-t-resource relative mt-2 rounded-md border border-t-4 p-6 sm:p-8">
        {r.status !== "published" && (
          <div className="absolute -top-4 right-4">
            <Stamp>{r.status === "hidden" ? "Hidden" : "In review"}</Stamp>
          </div>
        )}
        <p className="text-step--1 text-resource font-mono tracking-widest">{r.call_number}</p>
        <h1 className="font-display text-step-4 mt-1">{r.title}</h1>
        <p className="text-muted mt-2">
          Added by {r.author.display_name} ·{" "}
          <time dateTime={r.created_at}>{new Date(r.created_at).toLocaleDateString("en-GB")}</time>
        </p>
        <p className="mt-4 flex flex-wrap gap-2">
          <Badge tone="resource">{r.resource_type}</Badge>
          <Badge>{r.difficulty}</Badge>
          {r.category && <Badge>{r.category}</Badge>}
          {time && <Badge>{time}</Badge>}
          {r.is_research && <Badge tone="research">research</Badge>}
        </p>
        {r.hidden_reason && (
          <Callout tone="warning" title="Hidden by moderators" className="mt-4">
            {r.hidden_reason}
          </Callout>
        )}
        <p className="text-step-1 mt-6 max-w-prose">{r.description}</p>

        <h2 className="font-display text-step-2 mt-8">Where to find it</h2>
        <ul className="mt-2 flex flex-col">
          {r.links.map((l) => (
            <li key={l.id}>
              <a
                href={l.url}
                target="_blank"
                rel="noopener nofollow ugc"
                className="text-accent inline-flex min-h-11 items-center gap-2 underline underline-offset-4"
              >
                <Icon name="link" size={16} />
                {l.label || new URL(l.url).hostname}
                <span className="sr-only">(opens in a new tab)</span>
              </a>
            </li>
          ))}
        </ul>

        <dl className="mt-8 grid gap-5 sm:grid-cols-2">
          <Field label="Before you start">{r.prerequisites}</Field>
          <Field label="Best part">{r.best_part}</Field>
        </dl>
        {r.warning && (
          <Callout tone="warning" title="Heads up" className="mt-6">
            {r.warning}
          </Callout>
        )}
        {r.student_note && (
          <div className="relative mt-6">
            <Marginalia>{r.student_note}</Marginalia>
          </div>
        )}

        {r.tags.length > 0 && (
          <ul aria-label="Tags" className="mt-8 flex flex-wrap gap-x-3">
            {r.tags.map((t) => (
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
        <ResourceActions
          resource={r}
          reportAuthor={r.author.id}
          className="border-rule mt-4 border-t pt-4"
        />
      </article>
      <Comments itemId={r.id} count={r.comment_count} />
    </main>
  );
}
