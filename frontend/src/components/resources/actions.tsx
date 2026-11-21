"use client";

import { IconButton } from "@/components/ui/button";
import { cn } from "@/components/ui/cn";
import { useResourceActions, type Votable } from "@/lib/api/content";

/** Vote arrows with the score between them, plus the bookmark ribbon. All optimistic. */
export function ResourceActions({
  resource,
  className,
}: {
  resource: Votable;
  className?: string;
}) {
  const { vote, toggleBookmark } = useResourceActions(resource);
  return (
    <div className={cn("relative flex flex-wrap items-center gap-2", className)}>
      <div role="group" aria-label="Vote" className="flex items-center">
        <IconButton
          label="Upvote"
          icon="arrow-up"
          aria-pressed={resource.my_vote === 1}
          className={cn(resource.my_vote === 1 && "text-accent")}
          onClick={() => vote(1)}
        />
        <span
          aria-label={`Score ${resource.vote_score}`}
          className="text-step-0 min-w-8 text-center font-mono tabular-nums"
        >
          {resource.vote_score}
        </span>
        <IconButton
          label="Downvote"
          icon="arrow-down"
          aria-pressed={resource.my_vote === -1}
          className={cn(resource.my_vote === -1 && "text-flame-text")}
          onClick={() => vote(-1)}
        />
      </div>
      <IconButton
        label={resource.bookmarked ? "Remove bookmark" : "Bookmark"}
        icon="bookmark"
        aria-pressed={resource.bookmarked}
        className={cn(resource.bookmarked && "text-accent [&_path]:fill-current")}
        onClick={toggleBookmark}
      />
      <span className="text-step--1 text-muted font-mono tabular-nums">
        {resource.bookmark_count} saved
      </span>
    </div>
  );
}
