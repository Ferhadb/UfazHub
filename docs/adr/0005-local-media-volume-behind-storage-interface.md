# 0005. Local media volume behind a storage interface

Status: accepted

## Context

Uploads (attachments, covers, avatars) must not live in the database. The target is a single EC2 host, but moving to S3 later must not touch feature code.

## Decision

Code talks to a small storage interface (put, open, delete, signed URL). The first implementation writes to `MEDIA_ROOT`, a named Docker volume mounted at `/app/media` in both backend and worker. MIME type is detected by content sniffing, sizes are limited, image variants are generated, a virus-scan hook runs before a file is accepted, and downloads use signed URLs.

## Consequences

Zero extra infrastructure now. The volume is outside the Postgres dump, so the runbook backs it up separately. An S3 implementation can replace the local one behind the same interface.
