# 0001. Joined-table content model

Status: accepted

## Context

Resources, articles, collections, questions and answers share tags, votes, bookmarks, comments, reports, moderation state and view counts. v1 used polymorphic `(type, id)` pairs, so foreign keys were not real and orphans were possible.

## Decision

A `content_items` base table holds the shared columns (id, kind, author, status, counters, search vector). Each kind has its own table whose primary key is also a foreign key to `content_items.id` (joined-table inheritance in SQLAlchemy). Votes, bookmarks, comments, tags and reports reference `content_items.id`, so every foreign key is real. Votes are unique on `(user_id, item_id)`; denormalized counters are updated atomically in the same transaction.

## Consequences

Cross-type features (unified search, feeds, moderation queue) query one table. Per-type reads need a join. Adding a type means one new table plus a CHECK value.
