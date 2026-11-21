"use client";

import * as D from "@radix-ui/react-dialog";
import { useRouter } from "next/navigation";
import { useEffect, useId, useMemo, useRef, useState } from "react";
import { Highlight } from "@/components/highlight";
import { Stamp } from "@/components/ui/badge";
import { Button, IconButton } from "@/components/ui/button";
import { cn, tintTop, type Tint } from "@/components/ui/cn";
import { EmptyState } from "@/components/ui/empty-state";
import { Icon } from "@/components/ui/icons";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  hitHref,
  useDebounced,
  useSearch,
  type SearchHit,
  type SearchType,
} from "@/lib/search/use-search";

const TYPES: { value: SearchType; label: string; tint: Tint }[] = [
  { value: "all", label: "All", tint: "resource" },
  { value: "resource", label: "Resources", tint: "resource" },
  { value: "article", label: "Articles", tint: "article" },
  { value: "collection", label: "Collections", tint: "collection" },
  { value: "question", label: "Questions", tint: "question" },
];
const ORDER = ["resource", "article", "collection", "question"] as const;
const tintOf = (t: SearchHit["type"]): Tint => t;

/** Cmd/Ctrl+K: a full-screen card catalogue. Radix Dialog supplies the focus trap, Escape and focus return. */
export function SearchPalette() {
  const router = useRouter();
  const uid = useId();
  const input = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [tab, setTab] = useState<SearchType>("all");
  const [active, setActive] = useState(0);
  const q = useDebounced(text.trim());
  const search = useSearch(q, tab);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    const onOpen = () => setOpen(true);
    window.addEventListener("keydown", onKey);
    window.addEventListener("open-catalogue-search", onOpen);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("open-catalogue-search", onOpen);
    };
  }, []);

  const groups = useMemo(() => {
    const hits = q.length >= 2 ? (search.data ?? []) : [];
    return ORDER.map((t) => ({ type: t, hits: hits.filter((h) => h.type === t) })).filter(
      (g) => g.hits.length,
    );
  }, [q, search.data]);
  const flat = groups.flatMap((g) => g.hits);
  const optionId = (h: SearchHit) => `${uid}-${h.id}`;
  const current = flat[Math.min(active, flat.length - 1)];

  const go = (h: SearchHit) => {
    setOpen(false);
    router.push(hitHref(h));
  };
  const onKeyDown = (e: React.KeyboardEvent) => {
    if (!flat.length) return;
    const move = (to: number) => {
      e.preventDefault();
      setActive((to + flat.length) % flat.length);
    };
    if (e.key === "ArrowDown") move(active + 1);
    else if (e.key === "ArrowUp") move(active - 1);
    else if (e.key === "Home") move(0);
    else if (e.key === "End") move(flat.length - 1);
    else if (e.key === "Enter" && current) {
      e.preventDefault();
      go(current);
    }
  };

  return (
    <D.Root
      open={open}
      onOpenChange={(o) => {
        setOpen(o);
        if (!o) setText("");
      }}
    >
      <D.Trigger asChild>
        <Button variant="secondary" aria-label="Search" aria-keyshortcuts="Control+K Meta+K">
          <Icon name="search" size={18} />
          <span className="hidden sm:inline">Search</span>
          <kbd className="text-step--1 text-muted hidden font-mono sm:inline">Ctrl K</kbd>
        </Button>
      </D.Trigger>
      <D.Portal>
        <D.Content
          onOpenAutoFocus={(e) => {
            e.preventDefault();
            input.current?.focus();
          }}
          aria-describedby={undefined}
          className="bg-paper text-ink anim-fade fixed inset-0 z-(--z-modal) overflow-y-auto"
        >
          <div className="mx-auto flex min-h-full max-w-4xl flex-col gap-4 px-4 py-6 sm:px-8">
            <div className="flex items-center justify-between gap-4">
              <D.Title className="font-display text-step-2">Search the catalogue</D.Title>
              <D.Close asChild>
                <IconButton label="Close search" icon="close" />
              </D.Close>
            </div>
            <input
              ref={input}
              type="search"
              role="combobox"
              aria-label="Search"
              aria-expanded={flat.length > 0}
              aria-controls={`${uid}-list`}
              aria-autocomplete="list"
              aria-activedescendant={current ? optionId(current) : undefined}
              autoComplete="off"
              spellCheck={false}
              placeholder="Try “algebra”, “past exams”, “SQL”…"
              value={text}
              onChange={(e) => {
                setText(e.target.value);
                setActive(0);
              }}
              onKeyDown={onKeyDown}
              className="bg-card border-ink/40 text-step-2 font-display min-h-14 w-full rounded-md border-2 px-4 py-2"
            />

            <Tabs value={tab} onValueChange={(v) => (setTab(v as SearchType), setActive(0))}>
              <TabsList aria-label="Filter by type">
                {TYPES.map((t) => (
                  <TabsTrigger key={t.value} value={t.value} tint={t.tint}>
                    {t.label}
                  </TabsTrigger>
                ))}
              </TabsList>
              {TYPES.map((t) => (
                <TabsContent key={t.value} value={t.value} className="mt-6">
                  {t.value === tab && (
                    <div aria-busy={search.isFetching}>
                      <p className="sr-only" role="status">
                        {q.length >= 2 && search.data ? `${flat.length} results` : ""}
                      </p>
                      {q.length < 2 ? (
                        <p className="text-muted">Type at least two letters. Typos are forgiven.</p>
                      ) : search.isError ? (
                        <div role="alert" className="flex flex-col items-start gap-3">
                          <p>{search.error.message}</p>
                          <Button variant="secondary" onClick={() => search.refetch()}>
                            Try again
                          </Button>
                        </div>
                      ) : !search.data ? (
                        <div className="grid gap-4 sm:grid-cols-2">
                          <Skeleton lines={2} />
                          <Skeleton lines={2} />
                        </div>
                      ) : flat.length === 0 ? (
                        <EmptyState title="Nothing under that heading">
                          Try fewer words or another spelling. We forgive typos, not that many.
                        </EmptyState>
                      ) : (
                        <div
                          role="listbox"
                          id={`${uid}-list`}
                          aria-label="Search results"
                          className={cn(
                            "flex flex-col gap-8",
                            search.isPlaceholderData && "opacity-60",
                          )}
                        >
                          {groups.map((g) => (
                            <div key={g.type} role="group" aria-label={`${g.type}s`}>
                              <h2
                                role="presentation"
                                className="text-step--1 text-muted mb-3 font-mono tracking-widest uppercase"
                              >
                                {g.type}s
                              </h2>
                              <div role="presentation" className="grid gap-4 sm:grid-cols-2">
                                {g.hits.map((h) => (
                                  <Result
                                    key={h.id}
                                    id={optionId(h)}
                                    hit={h}
                                    selected={h === current}
                                    onHover={() => setActive(flat.indexOf(h))}
                                    onPick={() => go(h)}
                                  />
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </TabsContent>
              ))}
            </Tabs>
          </div>
        </D.Content>
      </D.Portal>
    </D.Root>
  );
}

function Result({
  id,
  hit,
  selected,
  onHover,
  onPick,
}: {
  id: string;
  hit: SearchHit;
  selected: boolean;
  onHover: () => void;
  onPick: () => void;
}) {
  return (
    <div
      id={id}
      role="option"
      aria-selected={selected}
      onMouseMove={onHover}
      onClick={onPick}
      className={cn(
        "bg-card shadow-paper border-rule cursor-pointer rounded-md border border-t-4 p-4",
        tintTop[hit.is_research ? "research" : tintOf(hit.type)],
        selected && "outline-accent outline-2 outline-offset-2",
      )}
    >
      <p className="text-step--1 text-muted flex items-center justify-between font-mono tracking-widest">
        {hit.call_number}
        {hit.is_research && (
          <Stamp tone="research" tilt={2}>
            Research
          </Stamp>
        )}
      </p>
      <p className="font-display text-step-1 mt-1">
        <Highlight text={hit.title_hl} />
      </p>
      <p className="text-muted mt-1 line-clamp-2">
        <Highlight text={hit.snippet} />
      </p>
    </div>
  );
}
