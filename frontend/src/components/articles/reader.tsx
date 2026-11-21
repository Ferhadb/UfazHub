"use client";

import Link from "next/link";
import { useMemo, useRef } from "react";
import { Comments } from "@/components/comments/comments";
import { CourseFiling } from "@/components/courses/course-filing";
import { ResourceActions } from "@/components/resources/actions";
import { Badge, Stamp } from "@/components/ui/badge";
import { Button, buttonClass } from "@/components/ui/button";
import { cn } from "@/components/ui/cn";
import { EmptyState } from "@/components/ui/empty-state";
import { Icon } from "@/components/ui/icons";
import { Marginalia } from "@/components/ui/marginalia";
import { Skeleton } from "@/components/ui/skeleton";
import { useArticle, useComments, type Article } from "@/lib/api/library";
import { useSession } from "@/lib/auth/use-session";
import { ArticleBody } from "./article-body";
import { Ribbon } from "./ribbon";
import { useReading } from "./use-reading";

const shell = "relative z-10 mx-auto max-w-3xl px-4 py-10";

/** Notes from the comments that fit in a margin: short ones, first three. */
function MarginNotes({ itemId }: { itemId: string }) {
  const q = useComments(itemId);
  const notes = (q.data?.pages[0]?.items ?? []).filter((c) => c.body.length <= 160).slice(0, 3);
  if (notes.length === 0) return null;
  return (
    <div className="no-print lg:static">
      {notes.map((c, i) => (
        // On lg+ each note sits in the right margin at a staggered height; below that it is an inline bubble.
        <div
          key={c.id}
          className="lg:absolute lg:left-0 lg:w-full"
          style={{ top: `${(i + 1) * 22}%` }}
        >
          <div className="relative">
            <Marginalia>
              {c.body}
              <span className="text-step--1 text-muted mt-1 block font-sans">
                {c.author.display_name}
              </span>
            </Marginalia>
          </div>
        </div>
      ))}
    </div>
  );
}

function Reader({ a }: { a: Article }) {
  const { user } = useSession();
  const articleRef = useRef<HTMLDivElement>(null);
  const ids = useMemo(() => a.toc.map((_, i) => `section-${i}`), [a.toc]);
  const { progress, active, resume, jumpToResume } = useReading(articleRef, a.id, ids);
  const canEdit = user && (user.id === a.author.id || user.role === "admin");

  return (
    <main id="main" className="relative z-10 mx-auto max-w-7xl px-4 py-8 sm:px-8 sm:py-12">
      <Ribbon progress={progress} />
      <header className="mx-auto max-w-3xl xl:ms-[calc(12rem+2.5rem)] xl:max-w-[40rem]">
        <Link
          href="/articles"
          className="no-print text-step--1 inline-flex min-h-11 items-center gap-1 underline-offset-4 hover:underline"
        >
          <Icon name="chevron-left" size={16} /> All articles
        </Link>
        {a.cover && (
          // eslint-disable-next-line @next/next/no-img-element -- signed, pre-sized variants from our API
          <img
            src={a.cover.urls.lg}
            alt=""
            width={a.cover.width ?? undefined}
            height={a.cover.height ?? undefined}
            className="shadow-paper mt-2 aspect-[16/9] w-full rounded-md object-cover"
          />
        )}
        <p className="text-step--1 text-article mt-6 flex flex-wrap items-center gap-3 font-mono tracking-widest">
          {a.call_number}
          {a.status !== "published" && (
            <Stamp tone="flame">
              {a.status === "draft" ? "Draft" : a.status === "hidden" ? "Hidden" : "In review"}
            </Stamp>
          )}
          {a.is_research && <Badge tone="research">research</Badge>}
        </p>
        <h1 className="font-display text-step-5 mt-2 leading-[0.95]">{a.title}</h1>
        <p className="text-muted mt-4">
          By {a.author.display_name} ·{" "}
          <time dateTime={a.published_at ?? a.created_at}>
            {new Date(a.published_at ?? a.created_at).toLocaleDateString(undefined, {
              day: "numeric",
              month: "long",
              year: "numeric",
            })}
          </time>{" "}
          · <span className="font-mono">{a.reading_minutes} min read</span>
        </p>
        {canEdit && (
          <Link
            href={`/articles/${a.slug}/edit`}
            className={buttonClass("secondary", "no-print mt-3")}
          >
            Edit
          </Link>
        )}
        {resume > 0 && progress < 0.05 && (
          <Button variant="secondary" className="no-print ms-2 mt-3" onClick={jumpToResume}>
            Continue reading · {Math.round(resume * 100)}%
          </Button>
        )}
      </header>

      <div className="mt-10 grid gap-x-10 lg:grid-cols-[minmax(0,40rem)_1fr] xl:grid-cols-[12rem_minmax(0,40rem)_1fr]">
        {a.toc.length > 0 && (
          <nav aria-label="In this article" className="no-print mb-8 xl:mb-0">
            <div className="xl:sticky xl:top-20">
              <p className="text-step--1 text-muted font-mono tracking-widest uppercase">
                In this article
              </p>
              <ol className="mt-2 flex flex-col">
                {a.toc.map((t, i) => (
                  <li key={ids[i]} className={cn(t.level === 3 && "ps-4")}>
                    <a
                      href={`#${ids[i]}`}
                      aria-current={active === ids[i] ? "location" : undefined}
                      className={cn(
                        "text-step--1 inline-flex min-h-11 items-center border-s-2 ps-3 hover:underline",
                        active === ids[i]
                          ? "border-flame text-ink font-semibold"
                          : "border-rule text-muted",
                      )}
                    >
                      {t.text}
                    </a>
                  </li>
                ))}
              </ol>
            </div>
          </nav>
        )}
        <div ref={articleRef} className={cn("relative", a.toc.length === 0 && "xl:col-start-2")}>
          <article>
            <ArticleBody html={a.body_html} headingIds={ids} />
          </article>
          <MarginNotes itemId={a.id} />
        </div>
      </div>

      <div className="mx-auto max-w-3xl xl:ms-[calc(12rem+2.5rem)] xl:max-w-[40rem]">
        <ul aria-label="Tags" className="no-print mt-10 flex flex-wrap gap-x-3">
          {a.tags.map((t) => (
            <li key={t}>
              <Link
                href={`/articles?tag=${encodeURIComponent(t.toLowerCase())}`}
                className="inline-flex min-h-11 items-center underline-offset-4 hover:underline"
              >
                #{t}
              </Link>
            </li>
          ))}
        </ul>
        <div className="no-print">
          <CourseFiling itemId={a.id} canEdit={Boolean(canEdit)} />
        </div>
        <ResourceActions
          resource={a}
          reportAuthor={a.author.id}
          className="no-print border-rule mt-2 border-t pt-4"
        />
        <Comments itemId={a.id} count={a.comment_count} />
      </div>
    </main>
  );
}

export function ArticleReader({ refId }: { refId: string }) {
  const q = useArticle(refId);
  if (q.isPending)
    return (
      <main id="main" className={shell}>
        <Skeleton lines={8} />
      </main>
    );
  if (q.isError) {
    const missing = (q.error as { status?: number }).status === 404;
    return (
      <main id="main" className={shell}>
        <EmptyState
          title={missing ? "That page is not in the binding" : "The page will not turn"}
          action={
            missing ? (
              <Link href="/articles" className={buttonClass("secondary")}>
                Back to articles
              </Link>
            ) : (
              <Button variant="secondary" onClick={() => q.refetch()}>
                Try again
              </Button>
            )
          }
        >
          {missing ? "It may be a draft, or it never existed." : q.error.message}
        </EmptyState>
      </main>
    );
  }
  return <Reader a={q.data} />;
}
