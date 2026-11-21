# Security review — slice 9

Reviewed 2026-11-21 against [OWASP ASVS 5.0.0](https://asvs.owasp.org/downloads/) (the current stable release). This is an **area-level Level 2 triage**, with selected requirement IDs where a concrete gap is known. `Verified` means the named control was checked in code or a local test; it does **not** attest to every requirement in that chapter. `Partial` means a known gap remains. `Unverified` means runtime evidence or a full requirement-by-requirement test is still needed. `N/A` means the feature is absent. This review does **not** claim ASVS L2 compliance. Full attestation requires assessing every applicable L1 and L2 requirement in the [versioned OWASP requirements](https://github.com/OWASP/ASVS/tree/v5.0.0_release/5.0).

## L2 checklist by applicable area

| ASVS 5.0 area | Status | Evidence and remaining work |
| --- | --- | --- |
| V1 Encoding and Sanitization | Partial | React escapes ordinary text; Markdown is sanitized server-side with `nh3` (`backend/app/services/markdown.py`). SQLAlchemy is used for data queries; `backend/tests/test_ssrf.py` exercises preview URL restrictions. A full audit of every HTML, URL, regex, mail, and dynamic query sink is outstanding. |
| V2 Validation and Business Logic | Partial | Pydantic schemas bound fields; service tests cover votes and other limits. Redis rate limiting in `backend/app/core/ratelimit.py` intentionally fails open on Redis errors. Abuse resilience during a Redis outage has not been demonstrated. |
| V3 Web Frontend Security | Partial | `nginx.conf` sends CSP, HSTS, `nosniff`, `frame-ancestors 'none'`, X-Frame-Options, and Referrer-Policy. CSP permits `'unsafe-inline'` for scripts and styles, so script injection defense is incomplete. No production response-header or browser CSP test has run. |
| V4 API and Web Service | Partial | FastAPI/Pydantic validate request bodies and use a common error envelope. `backend/app/main.py` uses an explicit credentialed CORS allowlist; production settings now reject HTTP, loopback, wildcard, and non-origin values. Endpoint-by-endpoint abuse and content-type testing remains outstanding. |
| V5 File Handling | Partial | `backend/app/services/uploads.py` sniffs signatures, caps byte size, uses generated storage keys, and re-encodes images; `backend/tests/test_uploads.py` covers representative cases. The scanner hook defaults to accept all files; PDFs are not malware-scanned. |
| V6 Authentication | Partial | Argon2id, uniform invalid-credential responses, email verification, reset tokens, and rate limits are implemented (`backend/app/core/security.py`, `backend/app/services/auth.py`, `backend/tests/test_auth.py`). At least 64-character passwords are accepted (128-character maximum). ASVS v5.0.0-6.2.11 and -6.2.12 require context-word and breached-password checks; these are absent. MFA is absent and its applicability needs product/risk review. |
| V7 Session Management | Partial | 15-minute access JWTs stay in memory; refresh tokens are hashed, rotated, and revoked on reuse. Refresh cookie is HttpOnly, SameSite=Lax, path `/api/auth`; production requires Secure. Cookie-authenticated refresh/logout require the CSRF header (`backend/app/api/auth.py`, `backend/app/api/deps.py`). Cross-tab refresh behavior and deployed cookie flags need browser verification. |
| V8 Authorization | Partial | Backend dependencies recheck identity, active status, verification, and admin role; `backend/tests/test_permissions.py` and moderation tests cover representative access paths. The complete role × endpoint matrix has not been independently verified. |
| V9 Self-contained Tokens | Partial | JWT decoding pins HS256, requires expiration and subject, and checks token type (`backend/app/core/security.py`). No independent JWT fuzzing or signing-key rotation procedure was verified. |
| V10 OAuth and OIDC | N/A | Application uses local email/password authentication; no OAuth or OIDC flows are implemented. |
| V11 Cryptography | Partial | `secrets.token_urlsafe`, SHA-256 hashes for opaque tokens, HMAC media/view receipts, and Argon2id password hashes are present. Production requires a non-default JWT key of at least 32 characters. Entropy, key custody, and rotation in the deployed environment are unverified. |
| V12 Secure Communication | Unverified | `nginx.conf` redirects HTTP to HTTPS, allows TLS 1.2/1.3, and sets one-year HSTS with `includeSubDomains`. Live certificate, TLS handshake, HSTS propagation, and backend network isolation were not tested. |
| V13 Configuration | Partial | Production startup rejects default/short JWT secret, insecure cookies, non-HTTPS `SITE_URL`, and unsafe CORS origins. CI includes `pip-audit` and `npm audit --audit-level=high`. Local advisory checks could not reach registries; see below. Container image and host hardening were not reviewed. |
| V14 Data Protection | Partial | Privacy page and view-receipt retention job exist; account and auth-token cleanup is implemented. Database/backup encryption, retention for all personal data, and production access controls were not verified. |
| V15 Secure Coding and Architecture | Partial | CI checks formatting, tests, schema drift, build, and dependency advisories. No full threat model, dependency provenance review, or manual penetration test exists in this review. |
| V16 Security Logging and Error Handling | Partial | Request IDs, structured logs, common error envelopes, and an admin audit log exist. Monitoring/alert delivery, log retention, log access, and redaction in production remain unverified. |
| V17 WebRTC | N/A | No WebRTC feature exists. |

## Focused control checks

- **CSP:** present on normal and `/_next/static/` production responses in `nginx.conf`. `script-src 'unsafe-inline'` is a material residual gap; the inline theme script in `frontend/src/app/layout.tsx` and Next hydration currently require a nonce/hash design before removing it. `style-src 'unsafe-inline'` should also be evaluated. Test in report-only mode before enforcement.
- **HSTS:** `max-age=31536000; includeSubDomains` is present with `always` on both nginx locations. Do not preload until every subdomain is confirmed HTTPS capable. Runtime delivery was not verified.
- **CORS:** FastAPI allows credentials only for configured origins. Production validation rejects insecure/malformed origins; `backend/.env.example` and `DEPLOYMENT.md` document `CORS_ORIGINS=["https://ufazhub.xyz"]`. Same-origin requests do not need CORS. Confirm the actual deployed environment value.
- **Cookies:** refresh token is HttpOnly, SameSite=Lax, scoped to `/api/auth`; CSRF token is intentionally readable by JavaScript, SameSite=Lax; view token is HttpOnly, SameSite=Lax. All use `COOKIE_SECURE`, which must be true in production. CSRF uses double submit on cookie-authenticated endpoints. Verify `Set-Cookie` on the live TLS site.
- **Proxy/IP:** production and dev nginx now replace inbound `X-Forwarded-For` with `$remote_addr`, protecting IP-based limits from client header spoofing through nginx. Uvicorn still trusts forwarded headers from any direct peer (`--forwarded-allow-ips='*'`); the production backend port is loopback-bound for debugging. Restrict direct host access to trusted operators and verify the network path after deployment.

## Dependency checks and validation

- `npm audit --audit-level=high --offline`: reported zero vulnerabilities from local cache only; **not a current advisory check**. Online `npm audit --audit-level=high --json` failed because `registry.npmjs.org` could not be resolved.
- `uv run --offline pip-audit`: failed because `pypi.org` could not be resolved. Neither result establishes that dependencies are vulnerability-free. Both commands remain CI gates and need a successful networked run.
- Focused config pytest cases were collected but could not execute: the session fixture calls Alembic against local Postgres before the tests, and that database was unavailable. Direct settings construction and static checks should be repeated in the full backend suite once Postgres is running.
- `nginx -t` could not run locally because nginx/Docker are unavailable. Validate generated compose config, nginx syntax, and the actual response headers on a staging host.

## Highest-priority remaining work

1. Replace script `'unsafe-inline'` with a nonce or hashes compatible with Next hydration and the theme bootstrap; verify the rendered site with a CSP report-only rollout.
2. Add breached/common/context-password screening (ASVS v5.0.0-6.2.11 and -6.2.12) with privacy-conscious lookup and tests.
3. Configure real upload malware scanning before treating PDF uploads as safe.
4. Run a complete ASVS 5.0.0 L1+L2 requirement-by-requirement assessment and live production/staging checks, including TLS, cookies, response headers, log protection, and a networked dependency audit.
