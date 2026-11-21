"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { VerifyNotice } from "@/app/submit/form";
import type { Draft } from "@/app/submit/draft";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { Input, Textarea } from "@/components/ui/field";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/toggles";
import { useToast } from "@/components/ui/toast";
import { api, errorInfo } from "@/lib/api/client";
import { uploadFile, useMarkdownPreview, type Article } from "@/lib/api/library";
import { useSession } from "@/lib/auth/use-session";
import { ArticleBody } from "./article-body";

const tagList = (s: string) =>
  s
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);

/** Create or edit an article: write/preview, cover upload, draft or publish. */
export function ArticleForm({
  article,
  onDraft,
}: {
  article?: Article;
  onDraft?: (d: Draft) => void;
}) {
  const router = useRouter();
  const toast = useToast();
  const { user } = useSession();
  const [title, setTitle] = useState(article?.title ?? "");
  const [excerpt, setExcerpt] = useState(article?.excerpt ?? "");
  const [body, setBody] = useState(article?.body_md ?? "");
  const [tags, setTags] = useState(article?.tags.join(", ") ?? "");
  const [research, setResearch] = useState(article?.is_research ?? false);
  const [cover, setCover] = useState<{ id: string; url: string } | null>(
    article?.cover?.urls.sm ? { id: article.cover.id, url: article.cover.urls.sm } : null,
  );
  const [mode, setMode] = useState<"write" | "preview">("write");
  const [busy, setBusy] = useState<"draft" | "publish" | "cover" | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const fileRef = useRef<HTMLInputElement>(null);
  const preview = useMarkdownPreview(body, mode === "preview" && body.trim().length >= 20);

  useEffect(
    () =>
      onDraft?.({
        kind: "article",
        title,
        blurb: excerpt || body.replace(/[#*_`>\[\]]/g, "").slice(0, 160),
        chips: [research ? "research" : "article", ...tagList(tags).slice(0, 2)],
      }),
    [onDraft, title, excerpt, body, tags, research],
  );

  const pickCover = async (file: File | undefined) => {
    if (!file) return;
    setBusy("cover");
    try {
      const a = await uploadFile(file, "cover");
      setCover({ id: a.id, url: a.urls.sm ?? "" });
    } catch (e) {
      toast({ title: "Cover not uploaded", description: (e as Error).message, tone: "danger" });
    } finally {
      setBusy(null);
    }
  };

  const save = async (publish: boolean) => {
    setProblem(null);
    setFields({});
    setBusy(publish ? "publish" : "draft");
    const payload = {
      title: title.trim(),
      excerpt: excerpt.trim(),
      body_md: body,
      tags: tagList(tags),
      is_research: research,
      cover_attachment_id: cover?.id ?? null,
      publish,
    };
    const { data, error } = article
      ? await api.PATCH("/api/articles/{item_id}", {
          params: { path: { item_id: article.id } },
          body: payload,
        })
      : await api.POST("/api/articles", { body: payload });
    setBusy(null);
    if (!data) {
      const info = errorInfo(error);
      setFields(info.fields);
      setProblem(Object.keys(info.fields).length ? "Some fields need another look." : info.message);
      return;
    }
    toast({
      title: data.status === "published" ? "Published" : "Draft saved",
      description: data.call_number,
      tone: "success",
    });
    router.push(`/articles/${data.slug}`);
  };

  return (
    <>
      {user && !user.email_verified && <VerifyNotice />}
      <form
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          void save(true);
        }}
        className="mt-8 flex flex-col gap-5"
      >
        {problem && <Callout tone="danger">{problem}</Callout>}
        <Input
          label="Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          error={fields.title}
        />
        <Textarea
          label="Excerpt (optional)"
          hint="One or two sentences for the card; left blank, it is taken from the text."
          rows={2}
          maxLength={300}
          value={excerpt}
          onChange={(e) => setExcerpt(e.target.value)}
          error={fields.excerpt}
        />
        <div>
          <div role="group" aria-label="Editor mode" className="flex gap-1">
            {(["write", "preview"] as const).map((m) => (
              <Button
                key={m}
                variant={mode === m ? "primary" : "secondary"}
                aria-pressed={mode === m}
                onClick={() => setMode(m)}
              >
                {m === "write" ? "Write" : "Preview"}
              </Button>
            ))}
          </div>
          <div className="mt-3">
            {mode === "write" ? (
              <Textarea
                label="Body (Markdown)"
                hint="Use ## and ### for headings; they become the table of contents."
                rows={16}
                value={body}
                onChange={(e) => setBody(e.target.value)}
                error={fields.body_md}
              />
            ) : body.trim().length < 20 ? (
              <p className="text-muted">Write at least a sentence to see it set in type.</p>
            ) : preview.isPending ? (
              <Skeleton lines={5} />
            ) : preview.isError ? (
              <Callout tone="danger">{preview.error.message}</Callout>
            ) : (
              <ArticleBody html={preview.data.body_html} />
            )}
          </div>
        </div>
        <Input
          label="Tags"
          hint="Comma separated, up to 8"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
          error={fields.tags}
        />
        <div className="flex flex-wrap items-center gap-3">
          <input
            ref={fileRef}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="sr-only"
            aria-label="Cover image file"
            onChange={(e) => void pickCover(e.target.files?.[0])}
          />
          <Button
            variant="secondary"
            loading={busy === "cover"}
            onClick={() => fileRef.current?.click()}
          >
            {cover ? "Replace cover" : "Add a cover"}
          </Button>
          {cover && (
            <>
              {/* eslint-disable-next-line @next/next/no-img-element -- signed variant from our API */}
              <img src={cover.url} alt="Cover preview" className="h-16 rounded-sm" />
              <Button variant="ghost" onClick={() => setCover(null)}>
                Remove cover
              </Button>
            </>
          )}
        </div>
        <Switch
          label="This is research (a paper, thesis or study)"
          checked={research}
          onCheckedChange={setResearch}
        />
        <div className="flex flex-wrap gap-3">
          <Button type="submit" loading={busy === "publish"} disabled={!user?.email_verified}>
            {article?.status === "published" ? "Save changes" : "Publish"}
          </Button>
          {article?.status !== "published" && (
            <Button
              variant="secondary"
              loading={busy === "draft"}
              disabled={!user?.email_verified}
              onClick={() => void save(false)}
            >
              Save draft
            </Button>
          )}
        </div>
      </form>
    </>
  );
}
