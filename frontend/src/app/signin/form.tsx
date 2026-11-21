"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { AuthShell } from "@/components/auth-shell";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { Input } from "@/components/ui/field";
import { errorInfo } from "@/lib/api/client";
import { safeNext } from "@/lib/auth/token";
import { useSession } from "@/lib/auth/use-session";

const schema = z.object({
  email: z.email("Enter a valid email address"),
  password: z.string().min(1, "Enter your password"),
});
type Values = z.infer<typeof schema>;

export function SignInForm() {
  const router = useRouter();
  const next = safeNext(useSearchParams().get("next"));
  const { status, login } = useSession();
  const [problem, setProblem] = useState<string | null>(null);
  const [banned, setBanned] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  useEffect(() => {
    if (status === "authenticated") router.replace(next);
  }, [status, next, router]);

  const onSubmit = handleSubmit(async (values) => {
    setProblem(null);
    setBanned(false);
    try {
      await login(values);
    } catch (e) {
      const info = errorInfo(e);
      setProblem(info.message);
      setBanned(info.code === "account_banned");
    }
  });

  return (
    <AuthShell title="Sign in" intro="Welcome back. Your shelf kept your place.">
      <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
        {problem && (
          <Callout tone="danger">
            {problem}
            {banned && (
              <>
                {" "}
                <Link href="/appeal" className="underline underline-offset-4">
                  Appeal this decision
                </Link>
              </>
            )}
          </Callout>
        )}
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
        <Button type="submit" loading={isSubmitting}>
          Sign in
        </Button>
      </form>
      <p className="mt-6 flex flex-wrap justify-between gap-2">
        <Link href="/reset" className="min-h-11 underline underline-offset-4">
          Forgot your password?
        </Link>
        <Link
          href={`/signup${next === "/" ? "" : `?next=${encodeURIComponent(next)}`}`}
          className="min-h-11 underline underline-offset-4"
        >
          Create an account
        </Link>
      </p>
    </AuthShell>
  );
}
