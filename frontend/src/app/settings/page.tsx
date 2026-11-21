"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ModerationHistory } from "@/components/moderation/history";
import { Callout } from "@/components/ui/callout";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { api, errorInfo } from "@/lib/api/client";
import { useSession } from "@/lib/auth/use-session";

export default function SettingsPage() {
  const router = useRouter();
  const toast = useToast();
  const { user, status, logout, logoutAll } = useSession();

  // Middleware only bounces browsers with no session hint; this covers an expired one.
  useEffect(() => {
    if (status === "anonymous") router.replace("/signin?next=/settings");
  }, [status, router]);

  if (!user)
    return (
      <main id="main" className="relative z-10 mx-auto max-w-2xl p-4">
        <Skeleton />
      </main>
    );

  const resend = async () => {
    const { response, error } = await api.POST("/api/auth/resend-verification");
    toast(
      response.ok
        ? { title: "Link sent", description: "Check your inbox.", tone: "success" }
        : { title: "Could not send", description: errorInfo(error).message, tone: "danger" },
    );
  };

  return (
    <main
      id="main"
      className="relative z-10 mx-auto flex max-w-2xl flex-col gap-6 px-4 py-10 sm:px-8"
    >
      <h1 className="font-display text-step-4">Settings</h1>
      <section
        aria-labelledby="account"
        className="bg-card shadow-paper border-rule rounded-md border p-4"
      >
        <h2 id="account" className="font-display text-step-1">
          Account
        </h2>
        <p className="mt-2">{user.display_name}</p>
        <p className="text-muted">{user.email}</p>
        <Badge className="mt-2">{user.role.replace("_", " ")}</Badge>
      </section>
      {!user.email_verified && (
        <Callout tone="warning" title="Confirm your email">
          Some actions unlock once your email is confirmed.
          <div className="mt-3">
            <Button variant="secondary" onClick={resend}>
              Resend the link
            </Button>
          </div>
        </Callout>
      )}
      {user.status !== "active" && (
        <Callout tone="danger" title={`Your account is ${user.status}`}>
          You cannot post, vote or comment. The history below says why and how to appeal.
        </Callout>
      )}
      <ModerationHistory />
      <section aria-labelledby="sessions" className="flex flex-wrap gap-3">
        <h2 id="sessions" className="sr-only">
          Sessions
        </h2>
        <Button variant="secondary" onClick={() => logout().then(() => router.replace("/"))}>
          Sign out
        </Button>
        <Button variant="danger" onClick={() => logoutAll().then(() => router.replace("/signin"))}>
          Sign out everywhere
        </Button>
      </section>
    </main>
  );
}
