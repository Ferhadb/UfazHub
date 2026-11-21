# 0002. Auth: httpOnly refresh cookie plus in-memory access token

Status: accepted

## Context

v1 kept long-lived tokens in browser storage, readable by any XSS, with no revocation.

## Decision

A short-lived access JWT lives only in JavaScript memory. A refresh token lives in an httpOnly, `Secure` (prod), `SameSite` cookie. Only its hash is stored server-side; each use rotates it, and reuse of a rotated token revokes the whole family. Cookie endpoints require a CSRF check. Logout-everywhere revokes all of a user's refresh tokens. A single `useSession` hook handles silent refresh, so no component touches tokens.

## Consequences

A page reload needs one refresh call before the session is known. XSS cannot exfiltrate a long-lived credential. Revocation is real because refresh state is server-side.
