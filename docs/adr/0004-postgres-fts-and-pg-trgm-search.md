# 0004. Search with Postgres full-text and pg_trgm

Status: accepted

## Context

The platform needs one ranked search across all content types with highlighted snippets, filters and typo tolerance, at student-platform scale. v1 search was `LIKE` and untested against Postgres.

## Decision

`content_items` carries a weighted `tsvector` column with a GIN index, ranked with `ts_rank_cd`, snippets from `ts_headline`. The `pg_trgm` extension (enabled in migration 0001) with GIN trigram indexes on titles gives typo tolerance and powers duplicate detection. Tests run on real Postgres.

## Consequences

No extra service to run or back up. Ranking quality is bounded by Postgres; revisit (for example Meilisearch) only if load tests in the hardening slice show a need. Language configuration for Azerbaijani and Russian text is a known tuning point; `simple` plus trigram is the fallback.
