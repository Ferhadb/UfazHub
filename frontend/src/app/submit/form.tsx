"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { Draft } from "./draft";
import { Controller, useFieldArray, useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { Input, Select, Textarea } from "@/components/ui/field";
import { Icon } from "@/components/ui/icons";
import { Switch } from "@/components/ui/toggles";
import { useToast } from "@/components/ui/toast";
import { api, errorInfo } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { useSession } from "@/lib/auth/use-session";
import { DIFFICULTIES, RESOURCE_TYPES, submitSchema, type SubmitValues } from "./schema";

type Duplicate = components["schemas"]["DuplicateHit"];

export function VerifyNotice() {
  return (
    <Callout tone="warning" title="Verify your email first" className="mt-4">
      Posting opens once your email is confirmed. Check your inbox, or{" "}
      <Link href="/settings" className="underline">
        resend the link in settings
      </Link>
      .
    </Callout>
  );
}

export function SubmitForm({ onDraft }: { onDraft?: (d: Draft) => void }) {
  const router = useRouter();
  const toast = useToast();
  const { user } = useSession();
  const [problem, setProblem] = useState<string | null>(null);
  const [dupes, setDupes] = useState<Duplicate[]>([]);
  const {
    register,
    control,
    handleSubmit,
    getValues,
    watch,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<SubmitValues>({
    resolver: zodResolver(submitSchema),
    defaultValues: {
      title: "",
      description: "",
      resource_type: "article",
      difficulty: "beginner",
      category: "",
      minutes: "",
      prerequisites: "",
      best_part: "",
      warning: "",
      student_note: "",
      tags: "",
      is_research: false,
      links: [{ url: "", label: "" }],
    },
  });
  const links = useFieldArray({ control, name: "links" });

  useEffect(() => {
    const emit = (v: Partial<SubmitValues>) =>
      onDraft?.({
        kind: "resource",
        title: v.title ?? "",
        blurb: v.description ?? "",
        chips: [v.resource_type, v.difficulty].filter(Boolean) as string[],
      });
    emit(getValues());
    const sub = watch((v) => emit(v as Partial<SubmitValues>));
    return () => sub.unsubscribe();
  }, [watch, getValues, onDraft]);

  // Advisory only: warn about the same link or a similar title, never block.
  const checkDuplicates = async () => {
    const { url } = getValues("links.0");
    const title = getValues("title");
    if (!url.trim() && title.trim().length < 3) return;
    try {
      const { data } = await api.GET("/api/resources/duplicates", {
        params: { query: { url: url.trim() || undefined, title: title.trim() || undefined } },
      });
      setDupes(data ?? []);
    } catch {
      setDupes([]); // advisory only: a failed check must never get in the way
    }
  };

  const onSubmit = handleSubmit(async (v) => {
    setProblem(null);
    const { data, error } = await api.POST("/api/resources", {
      body: {
        title: v.title,
        description: v.description,
        resource_type: v.resource_type,
        difficulty: v.difficulty,
        category: v.category,
        time_commitment_minutes: v.minutes ? Number(v.minutes) : null,
        prerequisites: v.prerequisites,
        best_part: v.best_part,
        warning: v.warning,
        student_note: v.student_note,
        is_research: v.is_research,
        tags: v.tags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
        links: v.links,
      },
    });
    if (!data) {
      const { message, fields } = errorInfo(error);
      const known = Object.keys(fields).filter((k) => k in v || k.startsWith("links."));
      known.forEach((k) => setError(k as never, { message: fields[k] }));
      setProblem(known.length ? "Some fields need another look." : message);
      return;
    }
    toast({
      title: data.status === "published" ? "On the shelf" : "Received",
      description:
        data.status === "published"
          ? `${data.call_number} is live.`
          : `${data.call_number} will appear once a moderator has checked it.`,
      tone: "success",
    });
    router.push(`/resources/${data.call_number}`);
  });

  return (
    <>
      {user && !user.email_verified && <VerifyNotice />}
      <form onSubmit={onSubmit} noValidate className="mt-8 flex flex-col gap-5">
        {problem && <Callout tone="danger">{problem}</Callout>}
        <Input
          label="Title"
          error={errors.title?.message}
          {...register("title", { onBlur: checkDuplicates })}
        />
        <Textarea
          label="What is it, and who is it for?"
          error={errors.description?.message}
          {...register("description")}
        />

        <fieldset className="flex flex-col gap-4">
          <legend className="text-step--1 text-ink font-mono tracking-wide uppercase">Links</legend>
          {links.fields.map((f, i) => (
            <div key={f.id} className="flex flex-col gap-3 sm:flex-row sm:items-start">
              <div className="flex-1">
                <Input
                  label={`Link ${i + 1}`}
                  type="url"
                  inputMode="url"
                  placeholder="https://"
                  error={errors.links?.[i]?.url?.message}
                  {...register(`links.${i}.url`, { onBlur: i === 0 ? checkDuplicates : undefined })}
                />
              </div>
              <div className="sm:w-48">
                <Input
                  label="Label (optional)"
                  error={errors.links?.[i]?.label?.message}
                  {...register(`links.${i}.label`)}
                />
              </div>
              {links.fields.length > 1 && (
                <Button
                  variant="ghost"
                  className="sm:mt-7"
                  aria-label={`Remove link ${i + 1}`}
                  onClick={() => links.remove(i)}
                >
                  <Icon name="trash" />
                </Button>
              )}
            </div>
          ))}
          {links.fields.length < 5 && (
            <Button
              variant="secondary"
              className="self-start"
              onClick={() => links.append({ url: "", label: "" })}
            >
              <Icon name="plus" /> Add another link
            </Button>
          )}
        </fieldset>

        {dupes.length > 0 && (
          <Callout tone="warning" title="This may already be on the shelf">
            <ul className="mt-1">
              {dupes.map((d) => (
                <li key={d.call_number}>
                  <Link href={`/resources/${d.call_number}`} className="underline">
                    {d.call_number} · {d.title}
                  </Link>{" "}
                  <span className="text-muted">
                    ({d.match === "same_link" ? "same link" : "similar title"})
                  </span>
                </li>
              ))}
            </ul>
          </Callout>
        )}

        <div className="grid gap-5 sm:grid-cols-2">
          <Select label="Type" {...register("resource_type")}>
            {RESOURCE_TYPES.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </Select>
          <Select label="Difficulty" {...register("difficulty")}>
            {DIFFICULTIES.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </Select>
          <Input
            label="Category"
            hint="For example Mathematics"
            error={errors.category?.message}
            {...register("category")}
          />
          <Input
            label="Time commitment (minutes)"
            inputMode="numeric"
            error={errors.minutes?.message}
            {...register("minutes")}
          />
        </div>
        <Input
          label="Tags"
          hint="Comma separated, up to 8: algebra, past exams, L2"
          error={errors.tags?.message}
          {...register("tags")}
        />
        <Textarea
          label="Before you start (prerequisites)"
          rows={2}
          error={errors.prerequisites?.message}
          {...register("prerequisites")}
        />
        <Textarea
          label="The best part"
          rows={2}
          error={errors.best_part?.message}
          {...register("best_part")}
        />
        <Textarea
          label="Heads up (warnings)"
          rows={2}
          error={errors.warning?.message}
          {...register("warning")}
        />
        <Textarea
          label="Your note to other students"
          rows={2}
          error={errors.student_note?.message}
          {...register("student_note")}
        />
        <Controller
          control={control}
          name="is_research"
          render={({ field }) => (
            <Switch
              label="This is research (a paper, thesis or study)"
              checked={field.value}
              onCheckedChange={field.onChange}
            />
          )}
        />
        <Button type="submit" loading={isSubmitting} disabled={!user?.email_verified}>
          Submit for the shelf
        </Button>
      </form>
    </>
  );
}
