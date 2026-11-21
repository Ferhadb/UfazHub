"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { Skeleton } from "@/components/ui/skeleton";
import { errorInfo } from "@/lib/api/client";
import { useMyReputation, useReputationRules } from "@/lib/api/notifications";
import { useSession } from "@/lib/auth/use-session";

const sign = (n: number) => (n > 0 ? `+${n}` : String(n));

function MyHistory() {
  const { user } = useSession();
  const q = useMyReputation();
  const rows = q.data?.pages.flatMap((p) => p.items) ?? [];
  return (
    <section aria-labelledby="mine" className="mt-12">
      <h2 id="mine" className="font-display text-step-2">
        Your reputation{" "}
        <span className="text-flame-text font-mono tabular-nums">{user?.reputation ?? 0}</span>
      </h2>
      {q.isPending ? (
        <Skeleton lines={3} />
      ) : rows.length === 0 ? (
        <p className="text-muted mt-2">No points yet. Answer a question to get started.</p>
      ) : (
        <ul className="border-rule mt-3 divide-y border-y">
          {rows.map((r, i) => (
            <li key={i} className="flex items-center justify-between gap-4 py-2">
              <span>
                {r.reason.replace("_", " ")}
                {r.call_number && (
                  <span className="text-muted text-step--1 ms-2 font-mono">{r.call_number}</span>
                )}
              </span>
              <span className="font-mono tabular-nums">{sign(r.points)}</span>
            </li>
          ))}
        </ul>
      )}
      {q.hasNextPage && (
        <Button
          className="mt-4"
          variant="secondary"
          loading={q.isFetchingNextPage}
          onClick={() => q.fetchNextPage()}
        >
          Load more
        </Button>
      )}
    </section>
  );
}

export function ReputationView() {
  const { status } = useSession();
  const q = useReputationRules();
  return (
    <main id="main" className="relative z-10 mx-auto max-w-3xl px-4 py-8 sm:px-8 sm:py-12">
      <p className="text-step--1 text-question font-mono tracking-widest uppercase">
        The marking scheme
      </p>
      <h1 className="font-display text-step-4 mt-1">How reputation works</h1>
      <p className="text-muted mt-3 max-w-prose">
        Reputation is a running total of what the community thinks of your contributions. Every
        point below is written down in the code that awards it, nothing is hidden.
      </p>
      {q.isPending ? (
        <Skeleton lines={6} />
      ) : q.isError ? (
        <Callout tone="danger" title="The marking scheme is missing">
          <p>{errorInfo(q.error).message}</p>
          <Button className="mt-3" variant="secondary" onClick={() => q.refetch()}>
            Try again
          </Button>
        </Callout>
      ) : (
        <>
          <section aria-labelledby="points" className="mt-8">
            <h2 id="points" className="font-display text-step-2">
              Points
            </h2>
            <table className="border-rule mt-3 w-full border-y text-start">
              <caption className="sr-only">What earns or loses reputation</caption>
              <tbody className="divide-rule divide-y">
                {q.data.points.map((p) => (
                  <tr key={p.reason}>
                    <th scope="row" className="py-2 pe-4 text-start font-normal">
                      {p.label}
                    </th>
                    <td className="py-2 text-end font-mono tabular-nums">{sign(p.points)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-muted mt-3">
              Votes can earn you at most {q.data.daily_vote_cap} reputation per day. You never earn
              from your own votes or from accepting your own answer.
            </p>
          </section>
          <section aria-labelledby="privileges" className="mt-8">
            <h2 id="privileges" className="font-display text-step-2">
              Privileges
            </h2>
            <ul className="border-rule mt-3 divide-y border-y">
              {q.data.privileges.map((p) => (
                <li key={p.key} className="flex items-center justify-between gap-4 py-2">
                  <span>{p.label}</span>
                  <span className="font-mono tabular-nums">{p.threshold}</span>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
      {status === "authenticated" ? (
        <MyHistory />
      ) : status === "anonymous" ? (
        <p className="mt-8">
          <Link href="/signin" className="underline underline-offset-4">
            Sign in
          </Link>{" "}
          to see your own points.
        </p>
      ) : null}
    </main>
  );
}
