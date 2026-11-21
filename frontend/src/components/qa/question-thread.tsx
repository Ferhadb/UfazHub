"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Comments } from "@/components/comments/comments";
import { ResourceActions } from "@/components/resources/actions";
import { Avatar } from "@/components/ui/avatar";
import { Badge, Stamp } from "@/components/ui/badge";
import { Button, buttonClass } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { cn } from "@/components/ui/cn";
import { EmptyState } from "@/components/ui/empty-state";
import { Input, Textarea } from "@/components/ui/field";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { errorInfo } from "@/lib/api/client";
import {
  useAnswers,
  useQuestion,
  useThreadActions,
  type Answer,
  type Question,
} from "@/lib/api/qa";
import { useSession } from "@/lib/auth/use-session";
import { ViewTracker } from "@/components/view-tracker";

const shell = "relative z-10 mx-auto max-w-3xl px-4 py-8 sm:py-12";

/** The teacher's mark in the margin: the vote score, circled in red pen. */
function Mark({ score }: { score: number }) {
  return (
    <p
      aria-hidden="true" // the vote control beside the answer already announces the score
      className="border-flame-text text-flame-text font-display text-step-1 flex size-14 -rotate-6 items-center justify-center rounded-full border-2 tabular-nums"
    >
      {score > 0 ? `+${score}` : score}
    </p>
  );
}

function Sheet({
  answer,
  question,
  actions,
}: {
  answer: Answer;
  question: Question;
  actions: ReturnType<typeof useThreadActions>;
}) {
  const { user } = useSession();
  const toast = useToast();
  const [notes, setNotes] = useState(false);
  const isAsker = user?.id === question.author.id;
  const isAdmin = user?.role === "admin";
  const fail = (e: unknown) =>
    toast({ title: "That did not go through", description: errorInfo(e).message, tone: "danger" });
  return (
    <li
      id={answer.call_number}
      className={cn(
        "bg-card shadow-paper border-rule grid gap-4 rounded-md border p-4 sm:grid-cols-[4.5rem_1fr]",
        answer.accepted && "border-flame-text border-l-4",
      )}
    >
      <div className="flex items-center gap-3 sm:flex-col sm:items-center">
        <Mark score={answer.vote_score} />
      </div>
      <div className="min-w-0">
        <p className="text-step--1 text-muted flex flex-wrap items-center gap-x-3 gap-y-1 font-mono">
          <span>{answer.call_number}</span>
          {answer.accepted && <Stamp tilt={-3}>✓ checked</Stamp>}
          {answer.pinned && <Badge tone="question">Pinned</Badge>}
          {answer.status !== "published" && <Badge tone="flame">Awaiting review</Badge>}
        </p>
        {/* Plain text on purpose: answers are never rendered as HTML. */}
        <p className="mt-2 break-words whitespace-pre-line">{answer.body}</p>
        <p className="text-step--1 text-muted mt-3 flex items-center gap-2">
          <Avatar
            name={answer.author.display_name}
            src={answer.author.avatar_url ?? undefined}
            size={28}
          />
          {answer.author.display_name}
          <span className="font-mono tabular-nums">· {answer.author.reputation ?? 0} rep</span>
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <ResourceActions
            resource={{ ...answer, bookmark_count: 0 }}
            bookmarks={false}
            reportAuthor={answer.author.id}
          />
          {isAsker && answer.status === "published" && (
            <Button
              variant="secondary"
              loading={actions.accept.isPending}
              onClick={() =>
                actions.accept.mutate({ id: answer.id, on: !answer.accepted }, { onError: fail })
              }
            >
              {answer.accepted ? "Remove the check" : "Mark as checked"}
            </Button>
          )}
          {isAdmin && (
            <Button
              variant="ghost"
              loading={actions.pin.isPending}
              onClick={() =>
                actions.pin.mutate({ id: answer.id, on: !answer.pinned }, { onError: fail })
              }
            >
              {answer.pinned ? "Unpin" : "Pin"}
            </Button>
          )}
          <Button variant="ghost" aria-expanded={notes} onClick={() => setNotes(!notes)}>
            Notes ({answer.comment_count})
          </Button>
        </div>
        {notes && <Comments itemId={answer.id} count={answer.comment_count} />}
      </div>
    </li>
  );
}

function AnswerBox({ actions }: { actions: ReturnType<typeof useThreadActions> }) {
  const { user, status } = useSession();
  const toast = useToast();
  const [body, setBody] = useState("");
  if (status === "anonymous")
    return (
      <p className="mt-8">
        <Link href="/signin" className="underline underline-offset-4">
          Sign in
        </Link>{" "}
        to write an answer.
      </p>
    );
  if (!user) return null;
  if (!user.email_verified)
    return (
      <Callout tone="warning" title="Verify your email to answer" className="mt-8">
        Your account can read and vote; answers open once your email is confirmed.
      </Callout>
    );
  const submit = async () => {
    try {
      const a = await actions.answer.mutateAsync(body.trim());
      setBody("");
      if (a.status !== "published")
        toast({ title: "Received", description: "A moderator will check your answer first." });
    } catch (e) {
      toast({ title: "Could not post that", description: errorInfo(e).message, tone: "danger" });
    }
  };
  return (
    <form
      className="mt-8 flex flex-col items-start gap-3"
      onSubmit={(e) => {
        e.preventDefault();
        void submit();
      }}
    >
      <div className="w-full">
        <Textarea
          label="Your answer"
          rows={6}
          maxLength={10000}
          value={body}
          onChange={(e) => setBody(e.target.value)}
        />
      </div>
      <Button type="submit" loading={actions.answer.isPending} disabled={body.trim().length < 10}>
        Submit answer
      </Button>
    </form>
  );
}

function MergeBox({ actions }: { actions: ReturnType<typeof useThreadActions> }) {
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [of, setOf] = useState("");
  const [error, setError] = useState<string>();
  const submit = () =>
    actions.merge.mutate(of.trim(), {
      onSuccess: () => setOpen(false),
      onError: (e) => {
        const info = errorInfo(e);
        setError(info.fields.of ?? info.message);
        if (!info.fields.of)
          toast({ title: "Not merged", description: info.message, tone: "danger" });
      },
    });
  return (
    <div className="mt-4">
      <Button variant="ghost" aria-expanded={open} onClick={() => setOpen(!open)}>
        Mark as duplicate
      </Button>
      {open && (
        <form
          className="mt-2 flex flex-wrap items-start gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
        >
          <Input
            label="Original question"
            placeholder="QST-0001"
            value={of}
            error={error}
            onChange={(e) => setOf(e.target.value)}
          />
          <Button type="submit" className="sm:mt-7" loading={actions.merge.isPending}>
            Merge
          </Button>
        </form>
      )}
    </div>
  );
}

export function QuestionThread({ callNumber }: { callNumber: string }) {
  const router = useRouter();
  const mergedFrom = useSearchParams().get("merged");
  const { user } = useSession();
  const q = useQuestion(callNumber);
  const a = useAnswers(callNumber);
  // The hook needs a question; a stand-in is fine while loading because no mutation can fire yet.
  const actions = useThreadActions(q.data ?? ({ id: "", call_number: callNumber } as Question));
  const original = q.data?.duplicate_of?.call_number;

  useEffect(() => {
    // A merged question redirects to its original, remembering where we came from.
    if (original) router.replace(`/questions/${original}?merged=${callNumber}`);
  }, [original, callNumber, router]);

  if (q.isPending || original)
    return (
      <main id="main" className={shell}>
        <Skeleton lines={6} />
      </main>
    );
  if (q.isError)
    return (
      <main id="main" className={shell}>
        <EmptyState
          title={
            (q.error as { status?: number }).status === 404
              ? "No such question"
              : "The exam hall is locked"
          }
          action={
            <Link href="/questions" className={buttonClass("secondary")}>
              All questions
            </Link>
          }
        >
          {q.error.message}
        </EmptyState>
        <Button className="mt-4" variant="ghost" onClick={() => q.refetch()}>
          Try again
        </Button>
      </main>
    );
  const question = q.data;
  const answers = a.data?.pages.flatMap((p) => p.items) ?? [];
  const canMerge = user && (user.id === question.author.id || user.role === "admin");
  return (
    <main id="main" className={shell}>
      <ViewTracker itemId={question.id} published={question.status === "published"} />
      {mergedFrom && (
        <Callout tone="info" title="Merged" className="mb-6">
          {mergedFrom} was a duplicate of this question.
        </Callout>
      )}
      <article className="bg-card shadow-paper border-rule border-t-question rounded-md border border-t-8 p-5 sm:p-8">
        <p className="text-step--1 text-question flex flex-wrap gap-x-3 font-mono tracking-widest">
          <span>{question.call_number}</span>
          <span>{question.topic}</span>
        </p>
        <h1 className="font-display text-step-3 mt-1">{question.title}</h1>
        <p className="mt-4 break-words whitespace-pre-line">{question.body}</p>
        {question.linked_resource && (
          <p className="mt-4">
            About{" "}
            <Link
              href={`/resources/${question.linked_resource.call_number}`}
              className="underline underline-offset-4"
            >
              {question.linked_resource.call_number} {question.linked_resource.title}
            </Link>
          </p>
        )}
        <p className="text-step--1 text-muted mt-4">
          Asked by {question.author.display_name}
          {question.tags.length > 0 && <> · {question.tags.join(", ")}</>}
        </p>
        <ResourceActions
          resource={question}
          reportAuthor={question.author.id}
          className="border-rule mt-4 border-t pt-2"
        />
        {canMerge && <MergeBox actions={actions} />}
      </article>

      <h2 className="font-display text-step-2 mt-10">
        {question.answer_count} {question.answer_count === 1 ? "answer" : "answers"}
      </h2>
      <div className="mt-4" aria-live="polite">
        {a.isPending ? (
          <Skeleton lines={3} />
        ) : a.isError ? (
          <Callout tone="danger" title="The answers will not load">
            <p>{errorInfo(a.error).message}</p>
            <Button className="mt-3" variant="secondary" onClick={() => a.refetch()}>
              Try again
            </Button>
          </Callout>
        ) : answers.length === 0 ? (
          <p className="text-muted">No answers yet. Be the first to leave a footprint.</p>
        ) : (
          <ol className="flex flex-col gap-6">
            {answers.map((x) => (
              <Sheet key={x.id} answer={x} question={question} actions={actions} />
            ))}
          </ol>
        )}
        {a.hasNextPage && (
          <Button
            className="mt-6"
            variant="secondary"
            loading={a.isFetchingNextPage}
            onClick={() => a.fetchNextPage()}
          >
            Load more answers
          </Button>
        )}
      </div>
      <AnswerBox actions={actions} />
      <Comments itemId={question.id} count={question.comment_count} />
    </main>
  );
}
