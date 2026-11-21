"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ArticleForm } from "@/components/articles/article-form";
import { GpaButton } from "@/components/gpa-button";
import { CollectionForm } from "@/components/collections/collection-form";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { cn } from "@/components/ui/cn";
import { Skeleton } from "@/components/ui/skeleton";
import { useSession } from "@/lib/auth/use-session";
import type { Draft } from "./draft";
import { SubmitForm } from "./form";

const KINDS = [
  { id: "resource", label: "Resource", blurb: "A link worth sharing", ruling: "ruled-resource" },
  { id: "article", label: "Article", blurb: "Something you wrote", ruling: "ruled-article" },
  { id: "collection", label: "Collection", blurb: "A reading path", ruling: "ruled-collection" },
] as const;
type Kind = (typeof KINDS)[number]["id"];

const PREFIX = { resource: "RES", article: "ART", collection: "COL" } as const;

/** Notebook-style composer: pick a kind, the page rulings change, a live index card follows along. */
export function Composer() {
  const router = useRouter();
  const params = useSearchParams();
  const { user, status } = useSession();
  const initial = KINDS.find((k) => k.id === params.get("type"))?.id ?? "resource";
  const [kind, setKind] = useState<Kind>(initial);
  const [draft, setDraft] = useState<Draft | null>(null);
  const onDraft = useCallback((d: Draft) => setDraft(d), []);

  useEffect(() => {
    if (status === "anonymous") router.replace("/signin?next=/submit");
  }, [status, router]);

  if (!user)
    return (
      <main id="main" className="relative z-10 mx-auto max-w-2xl p-4">
        <Skeleton />
      </main>
    );

  const k = KINDS.find((x) => x.id === kind)!;
  const live = draft?.kind === kind ? draft : null;
  return (
    <main id="main" className="relative z-10 mx-auto max-w-5xl px-4 py-8 sm:py-12">
      <p className="text-step--1 text-resource font-mono tracking-widest uppercase">
        New catalogue card
      </p>
      <h1 className="font-display text-step-4 mt-1">Add to the library</h1>
      {user.role === "user" ? (
        <div className="bg-card border-rule mt-4 flex max-w-xl flex-col gap-3 rounded-md border p-4 sm:flex-row sm:items-center">
          <p className="text-muted text-step--1 flex-1">
            Your cards are reviewed before they go on the shelf. Verified UFAZ students publish
            instantly.
          </p>
          <GpaButton
            next="/submit"
            label="Verify with UFAZ GPA"
            className="sm:w-auto sm:shrink-0"
          />
        </div>
      ) : (
        <p className="text-muted mt-2">You are verified: your cards go straight onto the shelf.</p>
      )}
      <div role="group" aria-label="What are you adding?" className="mt-6 flex flex-wrap gap-2">
        {KINDS.map((x) => (
          <button
            key={x.id}
            type="button"
            aria-pressed={x.id === kind}
            onClick={() => setKind(x.id)}
            className={cn(
              "min-h-11 rounded-md border px-4 text-start",
              x.id === kind ? "bg-card shadow-paper border-ink" : "border-rule hover:bg-card",
            )}
          >
            <span className="font-display block">{x.label}</span>
            <span className="text-step--1 text-muted">{x.blurb}</span>
          </button>
        ))}
      </div>
      <div className="mt-6 grid items-start gap-8 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <div className={cn("ruled shadow-paper border-rule rounded-md border px-5 pb-8", k.ruling)}>
          {kind === "resource" && <SubmitForm onDraft={onDraft} />}
          {kind === "article" && <ArticleForm onDraft={onDraft} />}
          {kind === "collection" && <CollectionForm onDraft={onDraft} />}
        </div>
        <aside aria-label="Live preview" className="lg:sticky lg:top-6">
          <p className="text-step--1 text-muted mb-3 font-mono tracking-widest uppercase">
            Your card, as it will look
          </p>
          <Card
            callNumber={`${PREFIX[kind]}-····`}
            tint={kind}
            title={live?.title.trim() || "Untitled"}
            headingLevel={2}
            tilt={-1}
          >
            <p className="line-clamp-4">{live?.blurb.trim() || "Your description appears here."}</p>
            {live && live.chips.length > 0 && (
              <p className="mt-3 flex flex-wrap gap-2">
                {live.chips.map((c) => (
                  <Badge key={c} tone={kind}>
                    {c}
                  </Badge>
                ))}
              </p>
            )}
          </Card>
        </aside>
      </div>
    </main>
  );
}
