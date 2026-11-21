"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { AuthShell } from "@/components/auth-shell";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { Input, Textarea } from "@/components/ui/field";
import { api, errorInfo } from "@/lib/api/client";

const schema = z.object({
  email: z.email("Enter a valid email address"),
  password: z.string().min(1, "Enter your password"),
  message: z.string().trim().min(10, "Say a little more (10 characters)").max(1000),
});
type Values = z.infer<typeof schema>;

/** A suspended account cannot sign in, so the password proves who is appealing. */
export function AppealForm() {
  const [done, setDone] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  const onSubmit = handleSubmit(async (body) => {
    setProblem(null);
    const { error } = await api.POST("/api/auth/appeal", { body });
    if (error) setProblem(errorInfo(error).message);
    else setDone(true);
  });

  return (
    <AuthShell
      title="Appeal a suspension"
      intro="Tell the moderators why your account should be restored."
    >
      {done ? (
        <Callout tone="success" title="Appeal sent">
          A moderator will review it. Try signing in again once you have heard back.
        </Callout>
      ) : (
        <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
          {problem && <Callout tone="danger">{problem}</Callout>}
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
            autoComplete="current-password"
            error={errors.password?.message}
            {...register("password")}
          />
          <Textarea label="Your message" error={errors.message?.message} {...register("message")} />
          <Button type="submit" loading={isSubmitting}>
            Send appeal
          </Button>
        </form>
      )}
      <p className="mt-6">
        <Link href="/signin" className="min-h-11 underline underline-offset-4">
          Back to sign in
        </Link>
      </p>
    </AuthShell>
  );
}
