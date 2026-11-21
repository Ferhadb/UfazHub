"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { VerifyNotice } from "@/app/submit/form";
import type { Draft } from "@/app/submit/draft";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { Input, Textarea } from "@/components/ui/field";
import { Icon } from "@/components/ui/icons";
import { useToast } from "@/components/ui/toast";
import { api, errorInfo } from "@/lib/api/client";
import { useSession } from "@/lib/auth/use-session";
import { useDebounced, useSearch } from "@/lib/search/use-search";

type Entry = { id: string; call_number: string; title: string; note: string };

/** Build a collection: search for resources and articles, order them, annotate each. */
export function CollectionForm({ onDraft }: { onDraft?: (d: Draft) => void }) {
  const router = useRouter();
  const toast = useToast();
  const { user } = useSession();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState("");
  const [items, setItems] = useState<Entry[]>([]);
  const [term, setTerm] = useState("");
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const hits = useSearch(useDebounced(term.trim()), "all");

  useEffect(
    () =>
      onDraft?.({
        kind: "collection",
        title,
        blurb: description,
        chips: [`${items.length} ${items.length === 1 ? "item" : "items"}`],
      }),
    [onDraft, title, description, items.length],
  );

  const addable = (hits.data ?? []).filter(
    (h) => (h.type === "resource" || h.type === "article") && !items.some((i) => i.id === h.id),
  );
  const move = (i: number, d: -1 | 1) =>
    setItems((xs) => {
      const next = [...xs];
      [next[i], next[i + d]] = [next[i + d]!, next[i]!];
      return next;
    });

  const submit = async () => {
    setProblem(null);
    setFields({});
    if (items.length === 0) return setProblem("Add at least one resource or article.");
    setBusy(true);
    const { data, error } = await api.POST("/api/collections", {
      body: {
        title: title.trim(),
        description: description.trim(),
        is_research: false,
        tags: tags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
        items: items.map((i) => ({ item_id: i.id, note: i.note })),
      },
    });
    setBusy(false);
    if (!data) {
      const info = errorInfo(error);
      setFields(info.fields);
      setProblem(Object.keys(info.fields).length ? "Some fields need another look." : info.message);
      return;
    }
    toast({ title: "Shelved", description: data.call_number, tone: "success" });
    router.push(`/collections/${data.call_number}`);
  };

  return (
    <>
      {user && !user.email_verified && <VerifyNotice />}
      <form
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
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
          label="What ties these together?"
          rows={2}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          error={fields.description}
        />
        <Input
          label="Tags"
          hint="Comma separated, up to 8"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
          error={fields.tags}
        />

        <fieldset className="flex flex-col gap-3">
          <legend className="text-step--1 text-ink font-mono tracking-wide uppercase">
            Items ({items.length}/50)
          </legend>
          <Input
            label="Find a resource or article"
            type="search"
            value={term}
            onChange={(e) => setTerm(e.target.value)}
          />
          {term.trim().length >= 2 && (
            <ul aria-label="Search results" className="border-rule rounded-md border">
              {addable.length === 0 ? (
                <li className="text-muted p-3">
                  {hits.isPending ? "Searching…" : "No other match."}
                </li>
              ) : (
                addable.slice(0, 6).map((h) => (
                  <li key={h.id} className="flex items-center justify-between gap-2 px-3">
                    <span>
                      <span className="text-muted font-mono">{h.call_number}</span> {h.title}
                    </span>
                    <Button
                      variant="ghost"
                      disabled={items.length >= 50}
                      aria-label={`Add ${h.title}`}
                      onClick={() => {
                        setItems([
                          ...items,
                          { id: h.id, call_number: h.call_number, title: h.title, note: "" },
                        ]);
                        setTerm("");
                      }}
                    >
                      <Icon name="plus" />
                    </Button>
                  </li>
                ))
              )}
            </ul>
          )}
          <ol className="flex flex-col gap-3">
            {items.map((it, i) => (
              <li key={it.id} className="border-rule rounded-md border p-3">
                <div className="flex items-center justify-between gap-2">
                  <p>
                    <span className="text-muted font-mono">{i + 1}.</span> {it.title}
                  </p>
                  <div className="flex">
                    <Button
                      variant="ghost"
                      disabled={i === 0}
                      aria-label={`Move ${it.title} up`}
                      onClick={() => move(i, -1)}
                    >
                      <Icon name="arrow-up" />
                    </Button>
                    <Button
                      variant="ghost"
                      disabled={i === items.length - 1}
                      aria-label={`Move ${it.title} down`}
                      onClick={() => move(i, 1)}
                    >
                      <Icon name="arrow-down" />
                    </Button>
                    <Button
                      variant="ghost"
                      aria-label={`Remove ${it.title}`}
                      onClick={() => setItems(items.filter((x) => x.id !== it.id))}
                    >
                      <Icon name="trash" />
                    </Button>
                  </div>
                </div>
                <Textarea
                  label={`Note on ${it.call_number}`}
                  rows={2}
                  maxLength={500}
                  value={it.note}
                  onChange={(e) =>
                    setItems(
                      items.map((x) => (x.id === it.id ? { ...x, note: e.target.value } : x)),
                    )
                  }
                />
              </li>
            ))}
          </ol>
        </fieldset>
        <Button type="submit" loading={busy} disabled={!user?.email_verified}>
          Shelve this collection
        </Button>
      </form>
    </>
  );
}
