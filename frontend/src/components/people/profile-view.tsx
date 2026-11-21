"use client";

import Link from "next/link";
import { CardList, NothingYet } from "@/components/cards/item-card";
import { Avatar } from "@/components/ui/avatar";
import { Stamp, type BadgeTone } from "@/components/ui/badge";
import { Button, buttonClass } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useContributions } from "@/lib/api/cards";
import { usePerson, type Profile } from "@/lib/api/people";
import { useSession } from "@/lib/auth/use-session";
import { Heatmap } from "./heatmap";

const STAMP_TONES: BadgeTone[] = [
  "resource",
  "article",
  "collection",
  "question",
  "research",
  "flame",
];
const SOCIAL_LABEL = {
  github: "GitHub",
  linkedin: "LinkedIn",
  website: "Website",
  x: "X",
} as const;

const Line = ({ label, children }: { label: string; children: string }) =>
  children ? (
    <div className="border-rule border-b border-dashed py-1">
      <dt className="text-step--1 text-muted font-mono tracking-widest uppercase">{label}</dt>
      <dd className="font-display text-step-0">{children}</dd>
    </div>
  ) : null;

function Passport({ p, mine }: { p: Profile; mine: boolean }) {
  const memberNo = `UFZ-${p.id.slice(0, 8).toUpperCase()}`;
  const socials = Object.entries(p.socials);
  return (
    <section
      aria-labelledby="who"
      className="bg-card shadow-paper border-rule border-t-collection relative rounded-md border border-t-4 p-6 sm:p-8"
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 rounded-[inherit]"
        style={{ backgroundImage: "var(--paper-grain)", opacity: "var(--grain-opacity)" }}
      />
      <p className="text-step--1 text-collection relative font-mono tracking-widest uppercase">
        UFAZ Hub library card · {memberNo}
      </p>
      <div className="relative mt-4 flex flex-col gap-6 sm:flex-row">
        <Avatar name={p.display_name} src={p.avatar_url ?? undefined} size={112} />
        <div className="min-w-0 flex-1">
          <h1 id="who" className="font-display text-step-4">
            {p.display_name}
          </h1>
          <dl className="mt-3 grid gap-x-8 sm:grid-cols-2">
            <Line label="Faculty">{p.faculty}</Line>
            <Line label="Class of">{p.graduation_year ? String(p.graduation_year) : ""}</Line>
            <Line label="Current role">{p.job_title}</Line>
            <Line label="Member since">
              {new Date(p.joined_at).toLocaleDateString("en-GB", {
                month: "long",
                year: "numeric",
              })}
            </Line>
            <Line label="Reputation">{String(p.reputation)}</Line>
          </dl>
          {p.bio && <p className="mt-4 max-w-prose whitespace-pre-line">{p.bio}</p>}
          {socials.length > 0 && (
            <ul aria-label="Links" className="mt-3 flex flex-wrap gap-x-4">
              {socials.map(([k, url]) => (
                <li key={k}>
                  <a
                    href={url}
                    target="_blank"
                    rel="noopener nofollow ugc"
                    className="text-accent inline-flex min-h-11 items-center underline underline-offset-4"
                  >
                    {SOCIAL_LABEL[k as keyof typeof SOCIAL_LABEL] ?? k}
                    <span className="sr-only"> (opens in a new tab)</span>
                  </a>
                </li>
              ))}
            </ul>
          )}
          {mine && (
            <Link href="/settings" className={buttonClass("secondary", "mt-3")}>
              Edit profile
            </Link>
          )}
        </div>
      </div>
    </section>
  );
}

export function ProfileView({ id }: { id: string }) {
  const q = usePerson(id);
  const { user } = useSession();
  const contributions = useContributions(id);

  if (q.isPending)
    return (
      <main id="main" className="relative z-10 mx-auto max-w-4xl px-4 py-10">
        <Skeleton lines={6} />
      </main>
    );
  if (q.isError) {
    const missing = (q.error as { status?: number }).status === 404;
    return (
      <main id="main" className="relative z-10 mx-auto max-w-4xl px-4 py-10">
        <EmptyState
          title={missing ? "No such card-holder" : "The register is stuck"}
          action={
            missing ? (
              <Link href="/people" className={buttonClass("secondary")}>
                All people
              </Link>
            ) : (
              <Button variant="secondary" onClick={() => q.refetch()}>
                Try again
              </Button>
            )
          }
        >
          {missing ? "They may have left, or never joined." : q.error.message}
        </EmptyState>
      </main>
    );
  }
  const p = q.data;
  const filed = ["resource", "article", "collection", "question", "answer"] as const;
  return (
    <main
      id="main"
      className="relative z-10 mx-auto flex max-w-4xl flex-col gap-10 px-4 py-8 sm:px-8 sm:py-12"
    >
      <Link
        href="/people"
        className="text-step--1 inline-flex min-h-11 items-center underline-offset-4 hover:underline"
      >
        All people
      </Link>
      <Passport p={p} mine={user?.id === p.id} />

      <section aria-labelledby="stamps">
        <h2 id="stamps" className="font-display text-step-2">
          Stamps
        </h2>
        {p.badges.length === 0 ? (
          <p className="text-muted mt-2">No stamps yet. The first one is the easiest.</p>
        ) : (
          <ul className="mt-5 flex flex-wrap gap-x-5 gap-y-6">
            {p.badges.map((b, i) => (
              <li key={b.slug}>
                <Stamp tone={STAMP_TONES[i % STAMP_TONES.length]} tilt={[-3, 2, -2, 3][i % 4]}>
                  {b.name}
                </Stamp>
                <p className="text-step--1 text-muted mt-1 max-w-40">{b.description}</p>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="stitches">
        <h2 id="stitches" className="font-display text-step-2">
          Contributions
        </h2>
        <p className="text-step--1 text-muted mt-1 font-mono tabular-nums">
          {filed
            .filter((t) => p.counts[t])
            .map((t) => `${p.counts[t]} ${t}${p.counts[t] === 1 ? "" : "s"}`)
            .join(" · ") || "Nothing filed yet"}
        </p>
        <div className="mt-3">
          <Heatmap activity={p.activity} />
        </div>
      </section>

      <section aria-labelledby="filed">
        <h2 id="filed" className="font-display text-step-2">
          Filed by {p.display_name}
        </h2>
        <div className="mt-4">
          <CardList
            query={contributions}
            empty={
              <NothingYet>Nothing published yet. Be the first to leave a footprint.</NothingYet>
            }
          />
        </div>
      </section>
    </main>
  );
}
