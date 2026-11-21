"use client";

import { useEffect, useRef, useState } from "react";
import { sanitizeHtml } from "@/lib/sanitize";

/** Sanitized article HTML. Headings get ids (matched to the server's TOC by index) for scroll-spy. */
export function ArticleBody({ html, headingIds = [] }: { html: string; headingIds?: string[] }) {
  // First render is the server's HTML (hydration-safe); then the client's own sanitizer takes over.
  const [safe, setSafe] = useState(html);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => setSafe(sanitizeHtml(html)), [html]);
  useEffect(() => {
    ref.current?.querySelectorAll("h2, h3").forEach((h, i) => {
      if (headingIds[i]) h.id = headingIds[i];
    });
  }, [safe, headingIds]);

  return (
    <div
      ref={ref}
      className="article-body"
      // Sanitized twice: nh3 on the server, DOMPurify here.
      dangerouslySetInnerHTML={{ __html: safe }}
    />
  );
}
