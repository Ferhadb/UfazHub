"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { useFollowedTags, useForYou } from "@/lib/api/cards";
import { api } from "@/lib/api/client";
import { useFollowTag } from "@/lib/api/lists";
import { useSession } from "@/lib/auth/use-session";
import { useQuery } from "@tanstack/react-query";
import { CardList, NothingYet } from "./item-card";

function useTopTags() {
  return useQuery({
    queryKey: ["top-tags"],
    staleTime: 5 * 60_000,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/tags", { params: { query: { limit: 20 } } });
      if (!data) throw error;
      return data.items;
    },
  });
}

export function ForYouView() {
  const router = useRouter();
  const toast = useToast();
  const { status } = useSession();
  const feed = useForYou();
  const followed = useFollowedTags();
  const top = useTopTags();
  const follow = useFollowTag();

  useEffect(() => {
    if (status === "anonymous") router.replace("/signin?next=/for-you");
  }, [status, router]);

  const mine = new Set((followed.data ?? []).map((t) => t.slug));
  return (
    <main id="main" className="relative z-10 mx-auto max-w-5xl px-4 py-8 sm:px-8 sm:py-12">
      <h1 className="font-display text-step-4">For you</h1>
      <p className="text-muted mt-2 max-w-prose">
        New things under the tags you follow. Pick a few and the shelf fills itself.
      </p>
      <section aria-labelledby="tags" className="mt-6">
        <h2 id="tags" className="text-step--1 font-mono tracking-widest uppercase">
          Tags to follow
        </h2>
        {top.isPending || followed.isPending ? (
          <Skeleton lines={1} />
        ) : (
          <ul className="mt-2 flex flex-wrap gap-2">
            {[
              ...(top.data ?? []).map((t) => ({ slug: t.slug, name: t.name })),
              ...(followed.data ?? []),
            ]
              .filter((t, i, all) => all.findIndex((x) => x.slug === t.slug) === i)
              .map((t) => (
                <li key={t.slug}>
                  <Button
                    variant={mine.has(t.slug) ? "primary" : "secondary"}
                    aria-pressed={mine.has(t.slug)}
                    disabled={follow.isPending}
                    onClick={() =>
                      follow.mutate(
                        { slug: t.slug, on: !mine.has(t.slug) },
                        {
                          onError: (e) =>
                            toast({
                              title: "Could not follow",
                              description: e.message,
                              tone: "danger",
                            }),
                        },
                      )
                    }
                  >
                    #{t.name}
                  </Button>
                </li>
              ))}
          </ul>
        )}
      </section>
      <div className="mt-8">
        <CardList
          query={feed}
          empty={
            <NothingYet title="Your shelf is empty">
              {mine.size === 0 ? (
                "Follow a tag above to start filling it."
              ) : (
                <>
                  Nothing new under your tags yet. Browse{" "}
                  <Link href="/resources" className="underline">
                    all resources
                  </Link>
                  .
                </>
              )}
            </NothingYet>
          }
        />
      </div>
    </main>
  );
}
