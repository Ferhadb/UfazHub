"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { AuthShell } from "@/components/auth-shell";
import { Button, buttonClass } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { Input } from "@/components/ui/field";
import { api, errorInfo } from "@/lib/api/client";

export function ResetPassword() {
  const token = useSearchParams().get("token");
  return token ? <NewPassword token={token} /> : <RequestLink />;
}

function RequestLink() {
  const [sent, setSent] = useState(false);
  const schema = z.object({ email: z.email("Enter a valid email address") });
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema) });

  return (
    <AuthShell
      title="Forgot your password?"
      intro="We will email you a link that works for an hour."
    >
      {sent ? (
        <Callout tone="success">
          If that address has an account, a reset link is on its way.
        </Callout>
      ) : (
        <form
          noValidate
          className="flex flex-col gap-4"
          onSubmit={handleSubmit(async (body) => {
            await api.POST("/api/auth/password/forgot", { body });
            setSent(true); // same answer whether or not the account exists
          })}
        >
          <Input
            label="Email"
            type="email"
            autoComplete="email"
            error={errors.email?.message}
            {...register("email")}
          />
          <Button type="submit" loading={isSubmitting}>
            Send reset link
          </Button>
        </form>
      )}
      <p className="mt-6">
        <Link href="/signin" className="underline underline-offset-4">
          Back to sign in
        </Link>
      </p>
    </AuthShell>
  );
}

const newPassword = z.object({ password: z.string().min(8, "Use at least 8 characters").max(128) });

function NewPassword({ token }: { token: string }) {
  const [done, setDone] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof newPassword>>({ resolver: zodResolver(newPassword) });

  return (
    <AuthShell title="Choose a new password" stamp={done ? "Done" : undefined}>
      {done ? (
        <>
          <Callout tone="success">
            Password changed. Every other device has been signed out.
          </Callout>
          <Link href="/signin" className={buttonClass("primary", "mt-6 w-full")}>
            Sign in
          </Link>
        </>
      ) : (
        <form
          noValidate
          className="flex flex-col gap-4"
          onSubmit={handleSubmit(async ({ password }) => {
            setProblem(null);
            const { response, error } = await api.POST("/api/auth/password/reset", {
              body: { token, password },
            });
            if (response.ok) setDone(true);
            else setProblem(errorInfo(error).message);
          })}
        >
          {problem && (
            <Callout tone="danger">
              {problem}{" "}
              <Link href="/reset" className="underline underline-offset-4">
                Request a new link
              </Link>
            </Callout>
          )}
          <Input
            label="New password"
            type="password"
            autoComplete="new-password"
            hint="At least 8 characters."
            error={errors.password?.message}
            {...register("password")}
          />
          <Button type="submit" loading={isSubmitting}>
            Change password
          </Button>
        </form>
      )}
    </AuthShell>
  );
}
