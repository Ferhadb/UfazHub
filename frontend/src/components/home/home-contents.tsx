"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { GpaButton } from "@/components/gpa-button";
import { Button, buttonClass } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api/client";
import { useSession } from "@/lib/auth/use-session";
import { GPA_URL } from "@/lib/gpa";

type FeedItem = {
  id: string;
  title: string;
  description: string;
  href: string;
  type: string;
  score: number;
  created: string;
};

function useHome() {
  const locale = useLocale();
  const t = useTranslations("Home");
  return useQuery({
    queryKey: ["home", "editorial", locale],
    staleTime: 60_000,
    queryFn: async () => {
      const [resources, articles, collections, questions, tags, contributor, board] =
        await Promise.all([
          api.GET("/api/resources", { params: { query: { limit: 8 } } }),
          api.GET("/api/articles", { params: { query: { limit: 8 } } }),
          api.GET("/api/collections", { params: { query: { limit: 5 } } }),
          api.GET("/api/questions", { params: { query: { limit: 5 } } }),
          api.GET("/api/tags", { params: { query: { limit: 12 } } }),
          api.GET("/api/leaderboard/contributor-of-the-month"),
          api.GET("/api/leaderboard", { params: { query: { period: "all", limit: 6 } } }),
        ]);
      if (!resources.data || !articles.data || !collections.data || !questions.data || !tags.data)
        throw new Error(t("catalogueUnavailable"));
      const items: FeedItem[] = [
        ...resources.data.items.map((x) => ({
          id: x.id,
          title: x.title,
          description: x.description,
          href: `/resources/${x.call_number}`,
          type: x.type,
          score: x.vote_score,
          created: x.created_at,
        })),
        ...articles.data.items.map((x) => ({
          id: x.id,
          title: x.title,
          description: x.excerpt,
          href: `/articles/${x.call_number}`,
          type: x.type,
          score: x.vote_score,
          created: x.created_at,
        })),
        ...collections.data.items.map((x) => ({
          id: x.id,
          title: x.title,
          description: x.description,
          href: `/collections/${x.call_number}`,
          type: x.type,
          score: x.vote_score,
          created: x.created_at,
        })),
        ...questions.data.items.map((x) => ({
          id: x.id,
          title: x.title,
          description: x.topic,
          href: `/questions/${x.call_number}`,
          type: x.type,
          score: x.vote_score,
          created: x.created_at,
        })),
      ];
      return {
        items,
        featured: articles.data.items[0],
        collection: collections.data.items[0],
        question: questions.data.items[0],
        tags: tags.data.items,
        contributor: contributor.data,
        board: board.data ?? [],
      };
    },
  });
}

export function HomeContents() {
  const t = useTranslations("Home");
  const home = useHome();
  const { status } = useSession();
  const [tab, setTab] = useState("latest");
  const [pick, setPick] = useState<string>();
  const items = home.data?.items ?? [];
  const feed = [...items]
    .sort(
      tab === "top" ? (a, b) => b.score - a.score : (a, b) => b.created.localeCompare(a.created),
    )
    .slice(0, 6);
  const shuffle = () => {
    const resources = items.filter((item) => item.type === "resource");
    const selection = resources[Math.floor(Math.random() * resources.length)];
    if (selection) setPick(selection.href);
  };

  return (
    <main id="main" className="relative z-10 mx-auto max-w-6xl px-4 pb-20 sm:px-8">
      <section
        aria-labelledby="home-title"
        className="grid gap-10 pt-12 pb-10 lg:grid-cols-[1fr_20rem]"
      >
        <div>
          <p className="text-step--1 text-accent font-mono tracking-widest uppercase">
            {t("eyebrow")}
          </p>
          <h1 id="home-title" className="font-display text-step-5 mt-4 max-w-3xl">
            {t("headlineBefore")} <em className="text-accent">{t("headlineEmphasis")}</em>{" "}
            {t("headlineAfter")}
          </h1>
          <p className="text-step-1 text-muted mt-6 max-w-2xl">{t("intro")}</p>
          <button
            type="button"
            onClick={() => window.dispatchEvent(new Event("open-catalogue-search"))}
            className="border-rule bg-card text-muted hover:border-ink mt-8 flex min-h-14 w-full max-w-2xl items-center justify-between rounded-md border px-5 text-left"
          >
            <span>{t("searchPlaceholder")}</span>
            <span className="text-step--1 font-mono">⌘ K</span>
          </button>
          {home.data && home.data.tags.length > 0 && (
            <div className="text-step--1 text-muted mt-4 flex flex-wrap items-center gap-x-4 gap-y-1">
              <span className="font-mono uppercase">{t("browseTopics")}</span>
              {home.data.tags.slice(0, 6).map((tag) => (
                <Link
                  key={tag.slug}
                  href={`/resources?tag=${encodeURIComponent(tag.slug)}`}
                  className="text-accent inline-flex min-h-11 items-center font-semibold underline-offset-4 hover:underline"
                >
                  {tag.name}
                </Link>
              ))}
            </div>
          )}
        </div>
        <aside className="border-rule self-center lg:border-l lg:pl-8">
          <h2 className="font-display text-step-2">{t("shareAsideTitle")}</h2>
          <p className="text-muted mt-3">{t("shareAsideBody")}</p>
          <Link
            href="/submit"
            className="text-accent mt-4 inline-flex min-h-11 items-center font-semibold underline-offset-4 hover:underline"
          >
            {t("shareAsideCta")} →
          </Link>
        </aside>
      </section>
      <section
        aria-labelledby="research-heading"
        className="border-rule bg-card -mx-4 grid gap-5 border-b px-4 py-8 sm:-mx-8 sm:px-8 lg:grid-cols-[1fr_auto] lg:items-end"
      >
        <div>
          <p className="text-step--1 text-research font-mono tracking-widest uppercase">
            {t("researchLabel")}
          </p>
          <h2 id="research-heading" className="font-display text-step-3 mt-2">
            {t("researchTitle")}
          </h2>
          <p className="text-muted mt-2 max-w-2xl">{t("researchBody")}</p>
        </div>
        <div className="flex flex-wrap gap-x-5">
          <Link
            href="/research"
            className="text-accent inline-flex min-h-11 items-center font-semibold underline-offset-4 hover:underline"
          >
            {t("browseResearch")}
          </Link>
          <Link
            href="/submit?research=1"
            className="text-accent inline-flex min-h-11 items-center font-semibold underline-offset-4 hover:underline"
          >
            {t("shareResearch")}
          </Link>
        </div>
      </section>
      {home.isPending ? (
        <div className="mt-12">
          <Skeleton lines={6} />
        </div>
      ) : home.isError ? (
        <div role="alert" className="mt-12">
          <EmptyState
            title={t("catalogueErrorTitle")}
            action={<Button onClick={() => home.refetch()}>{t("tryAgain")}</Button>}
          >
            {t("catalogueErrorBody")}
          </EmptyState>
        </div>
      ) : (
        <>
          <section
            className="grid gap-8 py-12 lg:grid-cols-[1.4fr_1fr]"
            aria-labelledby="featured-heading"
          >
            <div>
              <p className="text-step--1 text-flame-text font-mono tracking-widest uppercase">
                {t("featuredLabel")}
              </p>
              <h2 id="featured-heading" className="font-display text-step-4 mt-3">
                {t("featuredTitle")}
              </h2>
              {home.data.featured ? (
                <Link
                  href={`/articles/${home.data.featured.call_number}`}
                  className="bg-card shadow-paper border-article mt-6 block rounded-md border border-t-4 p-7"
                >
                  <span className="text-step--1 text-article font-mono">
                    {home.data.featured.call_number}
                  </span>
                  <h3 className="font-display text-step-3 mt-4">{home.data.featured.title}</h3>
                  <p className="text-muted mt-4 line-clamp-3">{home.data.featured.excerpt}</p>
                  <p className="text-step--1 text-muted mt-8 font-mono">
                    {t("minutesRead", { minutes: home.data.featured.reading_minutes })} ·{" "}
                    {home.data.featured.author.display_name}
                  </p>
                </Link>
              ) : (
                <EmptyState title={t("firstStoryTitle")}>{t("firstStoryBody")}</EmptyState>
              )}
            </div>
            <div className="lg:pt-12">
              <p className="text-step--1 text-question font-mono tracking-widest uppercase">
                {t("questionOfTheDay")}
              </p>
              {home.data.question ? (
                <Link
                  href={`/questions/${home.data.question.call_number}`}
                  className="border-rule mt-4 block border-y py-6"
                >
                  <h3 className="font-display text-step-2">{home.data.question.title}</h3>
                  <p className="text-muted mt-3">{t("joinConversation")}</p>
                </Link>
              ) : (
                <p className="text-muted mt-4">
                  {t("noQuestion")}{" "}
                  <Link className="text-accent underline" href="/ask">
                    {t("askFirst")}
                  </Link>
                </p>
              )}
              <div className="border-rule mt-10 border-t pt-8">
                <p className="text-step--1 text-collection font-mono tracking-widest uppercase">
                  {t("campusLabel")}
                </p>
                <p className="font-display text-step-2 mt-3">{t("campusTitle")}</p>
                <p className="text-muted mt-2">{t("campusBody")}</p>
                <div className="mt-4 flex flex-wrap gap-x-5">
                  <Link className="text-accent underline" href="/courses">
                    {t("exploreCourses")}
                  </Link>
                  <Link className="text-accent underline" href="/people">
                    {t("meetContributors")}
                  </Link>
                </div>
              </div>
            </div>
          </section>
          <section
            className="border-rule grid gap-6 border-y py-10 md:grid-cols-[1fr_2fr]"
            aria-labelledby="collection-heading"
          >
            <div>
              <p className="text-step--1 text-collection font-mono tracking-widest uppercase">
                {t("collectionLabel")}
              </p>
              <h2 id="collection-heading" className="font-display text-step-3 mt-3">
                {t("collectionTitle")}
              </h2>
            </div>
            {home.data.collection ? (
              <Link
                href={`/collections/${home.data.collection.call_number}`}
                className="bg-card shadow-paper border-collection block rounded-md border-l-8 p-6"
              >
                <span className="text-step--1 text-muted font-mono">
                  {t("pieces", { count: home.data.collection.items.length })} ·{" "}
                  {home.data.collection.call_number}
                </span>
                <h3 className="font-display text-step-2 mt-3">{home.data.collection.title}</h3>
                <p className="text-muted mt-2">{home.data.collection.description}</p>
              </Link>
            ) : (
              <p className="text-muted">
                {t("noCollection")}{" "}
                <Link href="/collections" className="text-accent underline">
                  {t("browseShelf")}
                </Link>
              </p>
            )}
          </section>
          <section className="py-12" aria-labelledby="tags-heading">
            <p className="text-step--1 text-resource font-mono tracking-widest uppercase">
              {t("tagsLabel")}
            </p>
            <h2 id="tags-heading" className="font-display text-step-3 mt-3">
              {t("trendingTags")}
            </h2>
            {home.data.tags.length ? (
              <ul className="mt-6 flex flex-wrap gap-3">
                {home.data.tags.map((tag) => (
                  <li key={tag.slug}>
                    <Link
                      href={`/resources?tag=${encodeURIComponent(tag.slug)}`}
                      className="bg-card shadow-paper border-rule inline-flex min-h-11 items-center gap-3 rounded-sm border px-4 font-mono text-sm"
                    >
                      <span aria-hidden="true" className="text-flame-text">
                        ◇
                      </span>
                      {tag.name}
                      <span className="text-muted">{tag.count}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-muted mt-4">{t("noTags")}</p>
            )}
          </section>
          <div className="grid gap-10 lg:grid-cols-[1fr_17rem]">
            <section className="py-12" aria-labelledby="feed-heading">
              <div className="flex flex-wrap items-end justify-between gap-4">
                <div>
                  <p className="text-step--1 text-flame-text font-mono tracking-widest uppercase">
                    {t("arrivalsLabel")}
                  </p>
                  <h2 id="feed-heading" className="font-display text-step-3 mt-3">
                    {t("arrivalsTitle")}
                  </h2>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Button variant="secondary" onClick={shuffle}>
                    {t("shuffleResource")}
                  </Button>
                  {pick && (
                    <Link href={pick} className="text-accent underline">
                      {t("openPick")}
                    </Link>
                  )}
                </div>
              </div>
              <Tabs value={tab} onValueChange={setTab} className="mt-7">
                <TabsList aria-label={t("feedSort")}>
                  <TabsTrigger value="latest">{t("latest")}</TabsTrigger>
                  <TabsTrigger value="top" tint="article">
                    {t("top")}
                  </TabsTrigger>
                  <TabsTrigger value="for-you" tint="research">
                    {t("forYou")}
                  </TabsTrigger>
                </TabsList>
                <TabsContent value="latest">
                  {feed.length ? (
                    <FeedCards items={feed} />
                  ) : (
                    <EmptyState title={t("emptyFeedTitle")}>{t("emptyFeedBody")}</EmptyState>
                  )}
                </TabsContent>
                <TabsContent value="top">
                  {feed.length ? (
                    <FeedCards items={feed} />
                  ) : (
                    <EmptyState title={t("emptyTopTitle")}>{t("emptyTopBody")}</EmptyState>
                  )}
                </TabsContent>
                <TabsContent value="for-you">
                  <p className="text-muted mb-4">{t("forYouBody")}</p>
                  <Link
                    href={status === "authenticated" ? "/for-you" : "/signin?next=/for-you"}
                    className="text-accent inline-flex min-h-11 items-center underline"
                  >
                    {status === "authenticated" ? t("openYourFeed") : t("signInForFeed")}
                  </Link>
                </TabsContent>
              </Tabs>
            </section>
            <aside
              className="lg:border-rule py-12 lg:border-l lg:pl-8"
              aria-labelledby="board-heading"
            >
              <div className="flex items-baseline justify-between">
                <h2 id="board-heading" className="font-display text-step-2">
                  {t("contributors")}
                </h2>
                <Link
                  href="/people"
                  className="text-accent text-step--1 underline-offset-4 hover:underline"
                >
                  {t("allPeople")}
                </Link>
              </div>
              <ol className="divide-rule mt-4 divide-y">
                {home.data.board.map((row) => (
                  <li key={row.person.id}>
                    <Link
                      href={`/people/${row.person.id}`}
                      className="hover:bg-ink/5 flex min-h-11 items-center justify-between gap-3 py-2"
                    >
                      <span className="truncate">{row.person.display_name}</span>
                      <span className="text-muted text-step--1 font-mono">{row.points}</span>
                    </Link>
                  </li>
                ))}
              </ol>
            </aside>
          </div>
          <section className="border-rule border-t py-12" aria-labelledby="contributors-heading">
            <p className="text-step--1 text-research font-mono tracking-widest uppercase">
              {t("peopleLabel")}
            </p>
            <h2 id="contributors-heading" className="font-display text-step-3 mt-3">
              {t("spotlightTitle")}
            </h2>
            {home.data.contributor ? (
              <Link
                href={`/people/${home.data.contributor.person.id}`}
                className="bg-card shadow-paper border-rule mt-6 inline-block rounded-md border p-6"
              >
                <p className="font-display text-step-2">
                  {home.data.contributor.person.display_name}
                </p>
                <p className="text-muted mt-2">
                  {t("spotlightPoints", { points: home.data.contributor.points })}
                </p>
              </Link>
            ) : (
              <p className="text-muted mt-4">{t("noContributor")}</p>
            )}
          </section>
          <div
            aria-label={t("freshTags")}
            className="border-rule text-step--1 text-muted flex flex-wrap gap-x-6 gap-y-2 border-y py-4 font-mono uppercase"
          >
            {home.data.tags.slice(0, 8).map((tag) => (
              <span key={tag.slug}>✳ {tag.name}</span>
            ))}
          </div>
        </>
      )}
      <section
        aria-labelledby="suite-heading"
        className="bg-card border-rule shadow-paper mt-12 flex flex-wrap items-center justify-between gap-5 rounded-md border p-6 sm:p-8"
      >
        <div className="max-w-2xl">
          <h2 id="suite-heading" className="font-display text-step-2">
            {t("suiteTitle")}
          </h2>
          <p className="text-muted mt-2">{t("suiteBody")}</p>
        </div>
        {status === "authenticated" ? (
          <a href={GPA_URL} className={buttonClass("secondary")}>
            {t("suiteOpen")} <span aria-hidden>↗</span>
          </a>
        ) : (
          <GpaButton next="/" label={t("suiteJoin")} className="sm:w-auto" />
        )}
      </section>
      <section
        aria-label={t("typeSpecimens")}
        className="text-step--1 text-muted border-rule mt-16 border-t pt-6"
      >
        <h2 className="font-display text-step-1">{t("lettersFromShelves")}</h2>
        <p lang="az">Əə Iı İi Şş Çç Ğğ Öö Üü</p>
        <p lang="fr">é è ê à ç œ « »</p>
        <p lang="ru">Ёё Щщ Ыы</p>
      </section>
    </main>
  );
}

function FeedCards({ items }: { items: FeedItem[] }) {
  return (
    <ul className="border-rule divide-rule divide-y rounded-md border">
      {items.map((item) => (
        <li key={item.id}>
          <Link href={item.href} className="hover:bg-ink/5 block px-5 py-4">
            <span className="text-step--1 text-muted font-mono tracking-widest uppercase">
              {item.type} · {item.score}
            </span>
            <h3 className="font-display text-step-1 mt-1">{item.title}</h3>
            <p className="text-muted mt-1 line-clamp-2">{item.description}</p>
          </Link>
        </li>
      ))}
    </ul>
  );
}
