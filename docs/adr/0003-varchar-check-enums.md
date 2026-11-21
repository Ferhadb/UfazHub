# 0003. Enums as VARCHAR plus CHECK constraints

Status: accepted

## Context

Native Postgres enums are awkward in migrations (`ALTER TYPE ... ADD VALUE` cannot run inside a transaction on older paths, and removals are painful) and v1 enum drift went unnoticed.

## Decision

Enumerated columns (role, status, content kind, report reason, ...) are `VARCHAR` with a named CHECK constraint generated from the Python enum. CI runs `alembic upgrade head` then `alembic check`, so models and migrations cannot diverge. The migration test also runs downgrade and upgrade.

## Consequences

Changing the allowed values is a normal constraint swap in a migration. The database still rejects invalid values.
