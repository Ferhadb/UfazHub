import DOMPurify from "dompurify";

// Mirrors the server's nh3 allow-list (backend/app/services/markdown.py). The server already
// sanitized; this is the second wall, so a server-side bug alone cannot become XSS.
const TAGS = [
  ...["p", "br", "hr", "h2", "h3", "h4", "blockquote", "pre", "code", "em", "strong", "del"],
  ...["ul", "ol", "li", "a", "img", "table", "thead", "tbody", "tr", "th", "td", "sup", "sub"],
];
const REL = "noopener nofollow ugc";
let hooked = false;

export function sanitizeHtml(html: string): string {
  if (typeof window === "undefined") return html; // the server rendered nh3-clean HTML
  if (!hooked) {
    hooked = true;
    DOMPurify.addHook("afterSanitizeAttributes", (node) => {
      if (node.tagName === "A") {
        node.removeAttribute("target");
        node.setAttribute("rel", REL);
      }
    });
  }
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: TAGS,
    ALLOWED_ATTR: ["href", "title", "src", "alt", "class"],
    ALLOWED_URI_REGEXP: /^(?:https?|mailto):/i,
    ALLOW_DATA_ATTR: false,
  });
}
