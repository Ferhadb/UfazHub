"use client";

import Link from "next/link";
import { useState } from "react";
import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { Textarea } from "@/components/ui/field";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { errorInfo } from "@/lib/api/client";
import { useCommentMutations, useComments, type Comment } from "@/lib/api/library";
import { useSession } from "@/lib/auth/use-session";

const when = (iso: string) =>
  new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });

function Composer({
  itemId,
  parentId,
  label,
  onDone,
}: {
  itemId: string;
  parentId?: string;
  label: string;
  onDone?: () => void;
}) {
  const { create } = useCommentMutations(itemId);
  const toast = useToast();
  const [body, setBody] = useState("");
  const submit = async () => {
    try {
      await create.mutateAsync({ body: body.trim(), parent_id: parentId });
      setBody("");
      onDone?.();
    } catch (e) {
      toast({ title: "Could not post that", description: errorInfo(e).message, tone: "danger" });
    }
  };
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        void submit();
      }}
      className="flex flex-col items-start gap-2"
    >
      <div className="w-full">
        <Textarea
          label={label}
          rows={parentId ? 2 : 3}
          maxLength={2000}
          value={body}
          onChange={(e) => setBody(e.target.value)}
        />
      </div>
      <Button type="submit" loading={create.isPending} disabled={!body.trim()}>
        {parentId ? "Reply" : "Post note"}
      </Button>
    </form>
  );
}

function Entry({ c, itemId, canReply }: { c: Comment; itemId: string; canReply: boolean }) {
  const { user } = useSession();
  const { remove } = useCommentMutations(itemId);
  const toast = useToast();
  const [replying, setReplying] = useState(false);
  const mine = user?.id === c.author.id || user?.role === "admin";
  const del = () =>
    remove.mutate(c.id, {
      onError: (e) =>
        toast({ title: "Could not delete", description: errorInfo(e).message, tone: "danger" }),
    });
  return (
    <li className="flex gap-3">
      <Avatar name={c.author.display_name} src={c.author.avatar_url ?? undefined} size={36} />
      <div className="min-w-0 flex-1">
        <p className="text-step--1 text-muted">
          <span className="text-ink font-semibold">{c.author.display_name}</span> ·{" "}
          <time dateTime={c.created_at}>{when(c.created_at)}</time>
        </p>
        {/* Plain text on purpose: comments are never rendered as HTML. */}
        <p className="mt-1 break-words whitespace-pre-line">{c.body}</p>
        <p className="text-step--1 flex gap-1">
          {canReply && !c.parent_id && (
            <Button variant="ghost" aria-expanded={replying} onClick={() => setReplying(!replying)}>
              Reply
            </Button>
          )}
          {mine && (
            <Button variant="ghost" loading={remove.isPending} onClick={del}>
              Delete
              <span className="sr-only"> comment by {c.author.display_name}</span>
            </Button>
          )}
        </p>
        {replying && (
          <div className="mt-2">
            <Composer
              itemId={itemId}
              parentId={c.id}
              label={`Reply to ${c.author.display_name}`}
              onDone={() => setReplying(false)}
            />
          </div>
        )}
        {c.replies.length > 0 && (
          <ul className="border-rule mt-3 flex flex-col gap-4 border-s-2 ps-4">
            {c.replies.map((r) => (
              <Entry key={r.id} c={r} itemId={itemId} canReply={false} />
            ))}
          </ul>
        )}
      </div>
    </li>
  );
}

/** Threaded comments (one level of replies) for any content item. */
export function Comments({ itemId, count }: { itemId: string; count: number }) {
  const { user, status } = useSession();
  const q = useComments(itemId);
  const items = q.data?.pages.flatMap((p) => p.items) ?? [];
  const canPost = status === "authenticated" && user?.email_verified;
  return (
    <section aria-labelledby="comments-h" className="no-print mt-12">
      <h2 id="comments-h" className="font-display text-step-2">
        Notes in the margin <span className="text-muted font-mono text-base">{count}</span>
      </h2>
      <div className="mt-4">
        {status === "authenticated" && !user?.email_verified ? (
          <Callout tone="warning" title="Verify your email to comment">
            Your account can read and vote; notes open once your email is confirmed.
          </Callout>
        ) : canPost ? (
          <Composer itemId={itemId} label="Add a note" />
        ) : status === "anonymous" ? (
          <p>
            <Link href="/signin" className="underline underline-offset-4">
              Sign in
            </Link>{" "}
            to leave a note.
          </p>
        ) : null}
      </div>
      <div className="mt-8" aria-live="polite">
        {q.isPending ? (
          <Skeleton lines={3} />
        ) : q.isError ? (
          <Callout tone="danger" title="The notes will not load">
            <p>{errorInfo(q.error).message}</p>
            <Button className="mt-3" variant="secondary" onClick={() => q.refetch()}>
              Try again
            </Button>
          </Callout>
        ) : items.length === 0 ? (
          <p className="text-muted">No notes yet. Be the first to leave a footprint.</p>
        ) : (
          <ul className="flex flex-col gap-6">
            {items.map((c) => (
              <Entry key={c.id} c={c} itemId={itemId} canReply={Boolean(canPost)} />
            ))}
          </ul>
        )}
        {q.hasNextPage && (
          <Button
            className="mt-6"
            variant="secondary"
            loading={q.isFetchingNextPage}
            onClick={() => q.fetchNextPage()}
          >
            Load more notes
          </Button>
        )}
      </div>
    </section>
  );
}
