"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { VerifyNotice } from "@/app/submit/form";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { Input, Textarea } from "@/components/ui/field";
import { useToast } from "@/components/ui/toast";
import { api, errorInfo } from "@/lib/api/client";
import { useSimilar } from "@/lib/api/qa";
import { useSession } from "@/lib/auth/use-session";
import { useDebounced } from "@/lib/search/use-search";

// Mirrors the API's limits; the server stays the authority (its field errors are shown too).
const schema = z.object({
  title: z.string().trim().min(10, "Ask in at least 10 characters").max(200, "At most 200"),
  body: z.string().trim().min(10, "Give the details (10 characters or more)").max(5000),
  topic: z.string().trim().min(2, "Name the course or subject").max(60, "At most 60"),
  linked_resource: z
    .string()
    .trim()
    .max(16)
    .regex(/^(RES-\d+)?$/i, "A call number such as RES-0421"),
  tags: z.string().max(400),
});
type Values = z.infer<typeof schema>;

export function AskForm() {
  const router = useRouter();
  const toast = useToast();
  const { user } = useSession();
  const [problem, setProblem] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    watch,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { title: "", body: "", topic: "", linked_resource: "", tags: "" },
  });
  const similar = useSimilar(useDebounced(watch("title").trim(), 400));
  const hits = similar.data ?? [];

  const onSubmit = handleSubmit(async (v) => {
    setProblem(null);
    const { data, error } = await api.POST("/api/questions", {
      body: {
        title: v.title,
        body: v.body,
        topic: v.topic,
        linked_resource: v.linked_resource || null,
        tags: v.tags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
      },
    });
    if (!data) {
      const { message, fields } = errorInfo(error);
      const known = Object.keys(fields).filter((k) => k in v);
      known.forEach((k) => setError(k as keyof Values, { message: fields[k] }));
      setProblem(known.length ? "Some fields need another look." : message);
      return;
    }
    toast({
      title: data.status === "published" ? "Question posted" : "Received",
      description:
        data.status === "published"
          ? `${data.call_number} is open for answers.`
          : `${data.call_number} will appear once a moderator has checked it.`,
      tone: "success",
    });
    router.push(`/questions/${data.call_number}`);
  });

  return (
    <>
      {user && !user.email_verified && <VerifyNotice />}
      <form onSubmit={onSubmit} noValidate className="mt-8 flex flex-col gap-5">
        {problem && <Callout tone="danger">{problem}</Callout>}
        <Input label="Question" error={errors.title?.message} {...register("title")} />
        {hits.length > 0 && (
          <Callout tone="warning" title="Already asked?">
            <ul className="mt-1">
              {hits.map((h) => (
                <li key={h.call_number}>
                  <Link
                    href={`/questions/${h.call_number}`}
                    target="_blank"
                    rel="noopener"
                    className="underline underline-offset-4"
                  >
                    {h.call_number} {h.title}
                  </Link>{" "}
                  <span className="text-step--1 font-mono">
                    {h.answer_count} {h.answer_count === 1 ? "answer" : "answers"}
                    {h.has_accepted ? ", checked" : ""}
                  </span>
                </li>
              ))}
            </ul>
          </Callout>
        )}
        <Textarea label="Details" rows={6} error={errors.body?.message} {...register("body")} />
        <Input
          label="Course or subject"
          hint="For example Algorithms L2"
          error={errors.topic?.message}
          {...register("topic")}
        />
        <Input
          label="Linked resource (optional)"
          hint="The call number of the resource this is about"
          placeholder="RES-0421"
          error={errors.linked_resource?.message}
          {...register("linked_resource")}
        />
        <Input
          label="Tags"
          hint="Comma separated, up to 8"
          error={errors.tags?.message}
          {...register("tags")}
        />
        <Button type="submit" loading={isSubmitting} className="self-start">
          Post the question
        </Button>
      </form>
    </>
  );
}
