"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { AuthShell } from "@/components/auth-shell";
import { buttonClass } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { Skeleton } from "@/components/ui/skeleton";
import { api, errorInfo } from "@/lib/api/client";

type State = { kind: "working" } | { kind: "ok" } | { kind: "error"; message: string };

export function VerifyEmail() {
  const token = useSearchParams().get("token");
  const [state, setState] = useState<State>({ kind: "working" });
  const started = useRef(false); // links are single-use: never submit twice (Strict Mode, re-renders)

  useEffect(() => {
    if (!token || started.current) return;
    started.current = true;
    api.POST("/api/auth/verify-email", { body: { token } }).then(({ data, error }) => {
      setState(data ? { kind: "ok" } : { kind: "error", message: errorInfo(error).message });
    });
  }, [token]);

  return (
    <AuthShell title="Confirm your email" stamp={state.kind === "ok" ? "Verified" : undefined}>
      {!token ? (
        <Callout tone="warning">
          This page needs the link from your confirmation email. Open it from there.
        </Callout>
      ) : state.kind === "working" ? (
        <Skeleton lines={2} />
      ) : state.kind === "ok" ? (
        <>
          <Callout tone="success">Your email is confirmed. Welcome to the archive.</Callout>
          <Link href="/signin" className={buttonClass("primary", "mt-6 w-full")}>
            Sign in
          </Link>
        </>
      ) : (
        <>
          <Callout tone="danger">{state.message}</Callout>
          <p className="text-muted mt-4">Sign in and request a fresh link from your settings.</p>
          <Link href="/signin?next=/settings" className={buttonClass("secondary", "mt-4 w-full")}>
            Sign in
          </Link>
        </>
      )}
    </AuthShell>
  );
}
