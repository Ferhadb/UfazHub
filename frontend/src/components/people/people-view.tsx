"use client";

import Link from "next/link";
import { useState } from "react";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/field";
import { Skeleton } from "@/components/ui/skeleton";
import { errorInfo } from "@/lib/api/client";
import { usePeople, type Person } from "@/lib/api/people";
import { useDebounced } from "@/lib/search/use-search";
import { Leaderboard } from "./leaderboard";

export function PersonRow({ p }: { p: Person }) {
  return (
    <li className="bg-card shadow-paper border-rule flex items-center gap-4 rounded-md border p-4">
      <Avatar name={p.display_name} src={p.avatar_url ?? undefined} size={48} />
      <div className="min-w-0 flex-1">
        <Link
          href={`/people/${p.id}`}
          className="font-display text-step-1 inline-flex min-h-11 items-center underline-offset-4 hover:underline"
        >
          {p.display_name}
        </Link>
        <p className="text-step--1 text-muted">
          {[p.faculty, p.graduation_year ? `class of ${p.graduation_year}` : "", p.job_title]
            .filter(Boolean)
            .join(" · ") || "No details filed yet"}
        </p>
      </div>
      {p.role !== "user" && <Badge tone="collection">{p.role.replace("_", " ")}</Badge>}
      <span className="text-step--1 font-mono tabular-nums">{p.reputation} rep</span>
    </li>
  );
}

export function PeopleView() {
  const [name, setName] = useState("");
  const [faculty, setFaculty] = useState("");
  const [year, setYear] = useState("");
  const dName = useDebounced(name.trim());
  const dFaculty = useDebounced(faculty.trim());
  const dYear = useDebounced(year.trim());
  const filters = {
    q: dName || undefined,
    faculty: dFaculty || undefined,
    graduation_year: /^\d{4}$/.test(dYear) ? Number(dYear) : undefined,
  };
  const q = usePeople(filters);
  const people = q.data?.pages.flatMap((p) => p.items) ?? [];
  return (
    <main id="main" className="relative z-10 mx-auto max-w-6xl px-4 py-8 sm:px-8 sm:py-12">
      <p className="text-step--1 text-collection font-mono tracking-widest uppercase">
        Catalogue · People
      </p>
      <h1 className="font-display text-step-4 mt-1">Who is who</h1>
      <div className="mt-8 grid gap-10 lg:grid-cols-[1fr_20rem]">
        <div>
          <form
            role="search"
            aria-label="Find people"
            onSubmit={(e) => e.preventDefault()}
            className="grid gap-4 sm:grid-cols-3"
          >
            <Input label="Name" value={name} onChange={(e) => setName(e.target.value)} />
            <Input label="Faculty" value={faculty} onChange={(e) => setFaculty(e.target.value)} />
            <Input
              label="Class of"
              inputMode="numeric"
              maxLength={4}
              value={year}
              onChange={(e) => setYear(e.target.value)}
            />
          </form>
          <div className="mt-6" aria-live="polite">
            {q.isPending ? (
              <Skeleton lines={5} />
            ) : q.isError ? (
              <Callout tone="danger" title="The directory is misfiled">
                <p>{errorInfo(q.error).message}</p>
                <Button className="mt-3" variant="secondary" onClick={() => q.refetch()}>
                  Try again
                </Button>
              </Callout>
            ) : people.length === 0 ? (
              <EmptyState title="Nobody by that name">
                Try fewer filters, or leave a footprint of your own and be found.
              </EmptyState>
            ) : (
              <ul className="flex flex-col gap-3">
                {people.map((p) => (
                  <PersonRow key={p.id} p={p} />
                ))}
              </ul>
            )}
            {q.hasNextPage && (
              <div className="mt-8 flex justify-center">
                <Button
                  variant="secondary"
                  loading={q.isFetchingNextPage}
                  onClick={() => q.fetchNextPage()}
                >
                  Load more
                </Button>
              </div>
            )}
          </div>
        </div>
        <Leaderboard />
      </div>
    </main>
  );
}
