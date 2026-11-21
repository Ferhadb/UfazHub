"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { AuthShell } from "@/components/auth-shell";
import { buttonClass } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { errorInfo } from "@/lib/api/client";
import { safeNext } from "@/lib/auth/token";
import { useSession } from "@/lib/auth/use-session";
import { NEXT_KEY, STATE_KEY } from "@/lib/gpa";

/** GPA sends the student back here with a one-minute token in the URL fragment. */
export default function Page() {
  const router = useRouter();
  const { loginWithGpa } = useSession();
  const [problem, setProblem] = useState<string | null>(null);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return; // strict mode runs effects twice; the token is single use
    started.current = true;
    const token = new URLSearchParams(window.location.hash.slice(1)).get("token");
    let state: string | null = null;
    let next = "/";
    try {
      state = sessionStorage.getItem(STATE_KEY);
      next = safeNext(sessionStorage.getItem(NEXT_KEY));
      sessionStorage.removeItem(STATE_KEY);
      sessionStorage.removeItem(NEXT_KEY);
    } catch {
      /* handled below */
    }
    history.replaceState(null, "", window.location.pathname); // keep the token out of history
    if (!token || !state) {
      setProblem("That sign-in link was not started from this browser tab. Please try again.");
      return;
    }
    loginWithGpa({ token, state }).then(
      () => router.replace(next),
      (e) => setProblem(errorInfo(e).message),
    );
  }, [loginWithGpa, router]);

  return (
    <AuthShell title="Signing you in" intro="Confirming your UFAZ GPA account.">
      {problem ? (
        <>
          <Callout tone="danger">{problem}</Callout>
          <Link href="/signin" className={buttonClass("secondary", "mt-6 w-full")}>
            Back to sign in
          </Link>
        </>
      ) : (
        <p role="status" className="text-muted">
          One moment…
        </p>
      )}
    </AuthShell>
  );
}
