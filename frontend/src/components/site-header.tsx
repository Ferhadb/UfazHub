"use client";

import Link from "next/link";
import { Avatar } from "@/components/ui/avatar";
import { buttonClass } from "@/components/ui/button";
import { useSession } from "@/lib/auth/use-session";

export function SiteHeader() {
  const { user, status } = useSession();
  return (
    <header className="border-rule relative z-10 border-b">
      <nav
        aria-label="Main"
        className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-2 sm:px-8"
      >
        <Link href="/" className="font-display text-step-1 inline-flex min-h-11 items-center">
          UFAZ <span className="text-flame-text ml-1">Hub</span>
        </Link>
        <div className="flex items-center gap-2">
          <Link href="/design" className={buttonClass("ghost")}>
            Design
          </Link>
          {status === "authenticated" && user ? (
            <Link
              href="/settings"
              aria-label={`Settings for ${user.display_name}`}
              className="inline-flex min-h-11 min-w-11 items-center justify-center"
            >
              <Avatar name={user.display_name} />
            </Link>
          ) : status === "anonymous" ? (
            <Link href="/signin" className={buttonClass("primary")}>
              Sign in
            </Link>
          ) : null}
        </div>
      </nav>
    </header>
  );
}
