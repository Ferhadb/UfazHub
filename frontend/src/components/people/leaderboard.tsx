"use client";

import Link from "next/link";
import { useState } from "react";
import { Avatar } from "@/components/ui/avatar";
import { Stamp } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { errorInfo } from "@/lib/api/client";
import { useContributorOfTheMonth, useLeaderboard, type LeaderRow } from "@/lib/api/people";

function Row({ r }: { r: LeaderRow }) {
  return (
    <li className="flex items-center gap-3">
      <span className="text-step--1 text-muted w-6 text-right font-mono tabular-nums">
        {r.rank}
      </span>
      <Avatar name={r.person.display_name} src={r.person.avatar_url ?? undefined} size={32} />
      <Link
        href={`/people/${r.person.id}`}
        className="inline-flex min-h-11 min-w-0 flex-1 items-center truncate underline-offset-4 hover:underline"
      >
        {r.person.display_name}
      </Link>
      <span className="text-step--1 font-mono tabular-nums">{r.points}</span>
    </li>
  );
}

export function Leaderboard() {
  const [period, setPeriod] = useState<"month" | "all">("month");
  const q = useLeaderboard(period);
  const top = useContributorOfTheMonth();
  return (
    <aside aria-label="Leaderboard" className="flex flex-col gap-6">
      <section
        aria-labelledby="cotm"
        className="bg-card shadow-paper border-rule border-t-collection relative rounded-md border border-t-4 p-4"
      >
        <div className="absolute -top-3 right-3">
          <Stamp tone="collection" tilt={3}>
            This month
          </Stamp>
        </div>
        <h2 id="cotm" className="font-display text-step-1">
          Contributor of the month
        </h2>
        {top.isPending ? (
          <Skeleton lines={1} />
        ) : top.isError ? (
          <p className="text-muted mt-2">Could not load this. Try again later.</p>
        ) : top.data ? (
          <div className="mt-3 flex items-center gap-3">
            <Avatar
              name={top.data.person.display_name}
              src={top.data.person.avatar_url ?? undefined}
            />
            <div>
              <Link
                href={`/people/${top.data.person.id}`}
                className="inline-flex min-h-11 items-center underline underline-offset-4"
              >
                {top.data.person.display_name}
              </Link>
              <p className="text-step--1 text-muted font-mono tabular-nums">
                +{top.data.points} reputation
              </p>
            </div>
          </div>
        ) : (
          <p className="text-muted mt-2">Nobody yet. The month is young.</p>
        )}
      </section>
      <section aria-labelledby="board">
        <h2 id="board" className="font-display text-step-1">
          Leaderboard
        </h2>
        <Tabs value={period} onValueChange={(v) => setPeriod(v as typeof period)} className="mt-2">
          <TabsList aria-label="Period">
            <TabsTrigger tint="collection" value="month">
              This month
            </TabsTrigger>
            <TabsTrigger tint="collection" value="all">
              All time
            </TabsTrigger>
          </TabsList>
        </Tabs>
        <div className="mt-3" aria-live="polite">
          {q.isPending ? (
            <Skeleton lines={4} />
          ) : q.isError ? (
            <Callout tone="danger" title="The scoreboard fell off the wall">
              <p>{errorInfo(q.error).message}</p>
              <Button className="mt-3" variant="secondary" onClick={() => q.refetch()}>
                Try again
              </Button>
            </Callout>
          ) : q.data.length === 0 ? (
            <p className="text-muted">No points on the board yet.</p>
          ) : (
            <ol className="flex flex-col">
              {q.data.map((r) => (
                <Row key={r.person.id} r={r} />
              ))}
            </ol>
          )}
        </div>
      </section>
    </aside>
  );
}
