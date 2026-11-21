"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { Input, Textarea } from "@/components/ui/field";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { errorInfo } from "@/lib/api/client";
import { uploadFile } from "@/lib/api/library";
import { usePerson, useRemoveAvatar, useUpdateProfile } from "@/lib/api/people";

const url = z
  .string()
  .trim()
  .max(200)
  .refine(
    (v) => v === "" || /^https?:\/\/\S+\.\S+$/i.test(v),
    "A full link starting with https://",
  );

// Mirrors the API's limits; the server stays the authority (its field errors are shown too).
const schema = z.object({
  display_name: z.string().trim().min(1, "Your name is required").max(80, "At most 80"),
  bio: z.string().trim().max(500, "At most 500 characters"),
  faculty: z.string().trim().max(80, "At most 80"),
  graduation_year: z
    .string()
    .trim()
    .regex(/^(\d{4})?$/, "A four-digit year")
    .refine((v) => v === "" || (+v >= 1990 && +v <= 2100), "Between 1990 and 2100"),
  job_title: z.string().trim().max(120, "At most 120"),
  github: url,
  linkedin: url,
  website: url,
  x: url,
});
type Values = z.infer<typeof schema>;

export function ProfileForm({ userId }: { userId: string }) {
  const toast = useToast();
  const qc = useQueryClient();
  const person = usePerson(userId);
  const save = useUpdateProfile(userId);
  const removeAvatar = useRemoveAvatar(userId);
  const file = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  const p = person.data;
  useEffect(() => {
    if (!p) return;
    const s = p.socials as Record<string, string>;
    reset({
      display_name: p.display_name,
      bio: p.bio,
      faculty: p.faculty,
      graduation_year: p.graduation_year ? String(p.graduation_year) : "",
      job_title: p.job_title,
      github: s.github ?? "",
      linkedin: s.linkedin ?? "",
      website: s.website ?? "",
      x: s.x ?? "",
    });
  }, [p, reset]);

  if (person.isPending) return <Skeleton lines={5} />;
  if (person.isError || !p)
    return (
      <Callout tone="danger" title="Could not load your profile">
        <Button className="mt-3" variant="secondary" onClick={() => person.refetch()}>
          Try again
        </Button>
      </Callout>
    );

  const onSubmit = handleSubmit(async (v) => {
    try {
      await save.mutateAsync({
        display_name: v.display_name,
        bio: v.bio,
        faculty: v.faculty,
        graduation_year: v.graduation_year ? Number(v.graduation_year) : null,
        job_title: v.job_title,
        socials: { github: v.github, linkedin: v.linkedin, website: v.website, x: v.x },
      });
      void qc.invalidateQueries({ queryKey: ["session"] });
      toast({ title: "Profile saved", tone: "success" });
    } catch (e) {
      const { fields, message } = e as { fields?: Record<string, string>; message: string };
      const known = Object.entries(fields ?? {}).filter(([k]) => k.replace("socials.", "") in v);
      known.forEach(([k, m]) =>
        setError(k.replace("socials.", "") as keyof Values, { message: m }),
      );
      toast({
        title: "Not saved",
        description: known.length ? "Check the marked fields." : message,
        tone: "danger",
      });
    }
  });

  const upload = async (f: File | undefined) => {
    if (!f) return;
    setBusy(true);
    try {
      await uploadFile(f, "avatar");
      await qc.invalidateQueries({ queryKey: ["person", userId] });
    } catch (e) {
      toast({ title: "Photo not saved", description: errorInfo(e).message, tone: "danger" });
    } finally {
      setBusy(false);
      if (file.current) file.current.value = "";
    }
  };

  return (
    <form
      onSubmit={onSubmit}
      noValidate
      aria-labelledby="profile"
      className="bg-card shadow-paper border-rule flex flex-col gap-4 rounded-md border p-4"
    >
      <h2 id="profile" className="font-display text-step-1">
        Public profile
      </h2>
      <div className="flex flex-wrap items-center gap-4">
        <Avatar name={p.display_name} src={p.avatar_url ?? undefined} size={64} />
        <input
          ref={file}
          id="avatar-file"
          type="file"
          accept="image/png,image/jpeg,image/webp"
          className="sr-only"
          onChange={(e) => upload(e.target.files?.[0])}
        />
        <Button
          type="button"
          variant="secondary"
          loading={busy}
          onClick={() => file.current?.click()}
        >
          Change photo
        </Button>
        {p.avatar_url && (
          <Button
            type="button"
            variant="ghost"
            loading={removeAvatar.isPending}
            onClick={() => removeAvatar.mutate()}
          >
            Remove photo
          </Button>
        )}
      </div>
      <Input label="Name" error={errors.display_name?.message} {...register("display_name")} />
      <Textarea
        label="Bio"
        hint="Up to 500 characters."
        error={errors.bio?.message}
        {...register("bio")}
      />
      <div className="grid gap-4 sm:grid-cols-2">
        <Input label="Faculty" error={errors.faculty?.message} {...register("faculty")} />
        <Input
          label="Class of"
          inputMode="numeric"
          maxLength={4}
          error={errors.graduation_year?.message}
          {...register("graduation_year")}
        />
      </div>
      <Input label="Current role" error={errors.job_title?.message} {...register("job_title")} />
      <fieldset className="flex flex-col gap-4">
        <legend className="text-step--1 font-mono tracking-wide uppercase">Links</legend>
        <Input label="GitHub" error={errors.github?.message} {...register("github")} />
        <Input label="LinkedIn" error={errors.linkedin?.message} {...register("linkedin")} />
        <Input label="Website" error={errors.website?.message} {...register("website")} />
        <Input label="X" error={errors.x?.message} {...register("x")} />
      </fieldset>
      <div>
        <Button type="submit" loading={isSubmitting} disabled={!isDirty}>
          Save profile
        </Button>
      </div>
    </form>
  );
}
