"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { AuthShell } from "@/components/auth-shell";
import { GpaButton } from "@/components/gpa-button";
import { Button, buttonClass } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { Input } from "@/components/ui/field";
import { api, errorInfo } from "@/lib/api/client";
import { safeNext } from "@/lib/auth/token";

const schema = z.object({
  display_name: z.string().trim().min(1, "Tell us what to call you").max(80),
  email: z.email("Enter a valid email address"),
  password: z.string().min(8, "Use at least 8 characters").max(128),
});
type Values = z.infer<typeof schema>;

export function SignUpForm() {
  const next = safeNext(useSearchParams().get("next"));
  const [done, setDone] = useState<string | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  const onSubmit = handleSubmit(async (body) => {
    setProblem(null);
    const { data, error } = await api.POST("/api/auth/signup", { body });
    if (data) return setDone(data.email);
    const { message, fields } = errorInfo(error);
    const known = Object.keys(fields).filter((f) => f in schema.shape);
    known.forEach((f) => setError(f as keyof Values, { message: fields[f] }));
    if (!known.length) setProblem(message);
  });

  if (done)
    return (
      <AuthShell title="Check your inbox" stamp="Almost">
        <Callout tone="success">
          We sent a confirmation link to <strong>{done}</strong>. It works for 48 hours.
        </Callout>
        <Link href="/signin" className={buttonClass("secondary", "mt-6 w-full")}>
          Go to sign in
        </Link>
      </AuthShell>
    );

  return (
    <AuthShell title="Join the archive" intro="Free for students and alumni. It takes a minute.">
      <GpaButton next={next} label="Join with UFAZ GPA" />
      <p className="text-muted text-step--1 mt-2">
        Already on UFAZ GPA? You are verified as a UFAZ student straight away. New to both? GPA
        walks you through registering.
      </p>
      <p className="text-muted text-step--1 before:border-rule after:border-rule my-5 flex items-center gap-3 before:flex-1 before:border-t after:flex-1 after:border-t">
        or sign up with an email
      </p>
      <Callout tone="info">
        Accounts made this way are checked by an admin before they get the verified student badge.
      </Callout>
      <form onSubmit={onSubmit} noValidate className="mt-4 flex flex-col gap-4">
        {problem && <Callout tone="danger">{problem}</Callout>}
        <Input
          label="Name"
          autoComplete="name"
          error={errors.display_name?.message}
          {...register("display_name")}
        />
        <Input
          label="Email"
          type="email"
          autoComplete="email"
          error={errors.email?.message}
          {...register("email")}
        />
        <Input
          label="Password"
          type="password"
          autoComplete="new-password"
          hint="At least 8 characters."
          error={errors.password?.message}
          {...register("password")}
        />
        <Button type="submit" variant="secondary" loading={isSubmitting}>
          Create account
        </Button>
      </form>
      <p className="mt-6">
        Already registered?{" "}
        <Link href="/signin" className="underline underline-offset-4">
          Sign in
        </Link>
      </p>
    </AuthShell>
  );
}
