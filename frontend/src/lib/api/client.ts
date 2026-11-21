import createClient, { type Middleware } from "openapi-fetch";
import { getAccessToken, readCsrfCookie } from "@/lib/auth/token";
import type { paths } from "./schema";

// Injects the in-memory access token and the CSRF double-submit header; callers never touch either.
export const authMiddleware: Middleware = {
  onRequest({ request }) {
    const token = getAccessToken();
    if (token) request.headers.set("Authorization", `Bearer ${token}`);
    const csrf = readCsrfCookie();
    if (csrf && request.method !== "GET") request.headers.set("X-CSRF-Token", csrf);
    return request;
  },
};

// Schema paths already carry the /api prefix, so the base is the site origin (same-origin by default).
export const api = createClient<paths>({
  baseUrl:
    process.env.NEXT_PUBLIC_API_ORIGIN ??
    (typeof window === "undefined" ? "" : window.location.origin),
  credentials: "include", // httpOnly refresh cookie
  fetch: (req) => globalThis.fetch(req), // resolved per call so tests can stub fetch
});
api.use(authMiddleware);

/** The `{code, message, fields?}` envelope's message and per-field errors from an openapi-fetch error. */
export function errorInfo(error: unknown): { message: string; fields: Record<string, string> } {
  const e = (error ?? {}) as { message?: string; fields?: Record<string, string> };
  return { message: e.message ?? "Something went wrong. Try again.", fields: e.fields ?? {} };
}
