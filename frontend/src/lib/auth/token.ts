/* The access token lives in this module-level variable only: never localStorage, never a cookie.
 * Reloading the page drops it; useSession gets a new one from the httpOnly refresh cookie. */
let accessToken: string | null = null;

export const getAccessToken = () => accessToken;
export const setAccessToken = (token: string | null) => {
  accessToken = token;
};

const CSRF_COOKIE = "csrf_token";

/** The CSRF cookie is readable by design (double submit); it also tells us a session may exist. */
export function readCsrfCookie(): string | null {
  if (typeof document === "undefined") return null;
  const hit = document.cookie.split("; ").find((c) => c.startsWith(CSRF_COOKIE + "="));
  return hit ? decodeURIComponent(hit.slice(CSRF_COOKIE.length + 1)) : null;
}

/** Only same-site relative paths: `//evil.com` and `https://…` fall back to "/". */
export function safeNext(next: string | null | undefined): string {
  return next && next.startsWith("/") && !next.startsWith("//") && !next.includes("\\")
    ? next
    : "/";
}
