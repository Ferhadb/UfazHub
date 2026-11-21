import { NextResponse, type NextRequest } from "next/server";

// The access token lives only in browser memory, so the server cannot verify a session here.
// What it can see is the CSRF cookie, set at sign-in and cleared at sign-out (path "/"): a cheap
// hint to bounce signed-out visitors before the page renders. The API still enforces real auth.
const PROTECTED = [
  "/settings",
  "/bookmarks",
  "/for-you",
  "/notifications",
  "/submit",
  "/ask",
  "/admin",
];

export const isProtected = (path: string) =>
  PROTECTED.some((p) => path === p || path.startsWith(p + "/"));

export function middleware(req: NextRequest) {
  if (isProtected(req.nextUrl.pathname) && !req.cookies.has("csrf_token")) {
    const url = req.nextUrl.clone();
    url.pathname = "/signin";
    url.search = `?next=${encodeURIComponent(req.nextUrl.pathname + req.nextUrl.search)}`;
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: [
    "/settings/:path*",
    "/bookmarks/:path*",
    "/for-you/:path*",
    "/notifications/:path*",
    "/submit/:path*",
    "/ask/:path*",
    "/admin/:path*",
  ],
};
