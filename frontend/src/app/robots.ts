import type { MetadataRoute } from "next";
import { siteUrl } from "@/lib/seo";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: [
        "/admin",
        "/appeal",
        "/ask",
        "/bookmarks",
        "/for-you",
        "/lists",
        "/notifications",
        "/settings",
        "/signin",
        "/signup",
        "/submit",
        "/verify",
        "/reset",
      ],
    },
    sitemap: new URL("/sitemap.xml", siteUrl).toString(),
  };
}
