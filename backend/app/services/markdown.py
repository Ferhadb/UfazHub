"""Markdown to safe HTML: markdown-it without raw HTML, then an nh3 allow-list as the real gate."""

import re

import nh3
from markdown_it import MarkdownIt

_md = MarkdownIt("commonmark", {"html": False}).enable(["table", "strikethrough"])

TAGS = {
    "p", "br", "hr", "h2", "h3", "h4", "blockquote", "pre", "code", "em", "strong", "del",
    "ul", "ol", "li", "a", "img", "table", "thead", "tbody", "tr", "th", "td", "sup", "sub",
}  # fmt: skip
# h1 is the article title, so body headings start at h2 (client allow-list matches this).
ATTRS = {"a": {"href", "title"}, "img": {"src", "alt", "title"}, "code": {"class"}}
SCHEMES = {"http", "https", "mailto"}
LINK_REL = "noopener nofollow ugc"


def render(md: str) -> str:
    # Demote any h1 the author wrote; the page already has one.
    html = _md.render(md)
    html = re.sub(r"<(/?)h1>", r"<\1h2>", html)
    return nh3.clean(
        html,
        tags=TAGS,
        attributes=ATTRS,
        url_schemes=SCHEMES,
        link_rel=LINK_REL,
        strip_comments=True,
    )


def _inline_text(tok) -> str:
    return "".join(
        c.content for c in tok.children or [] if c.type in ("text", "code_inline")
    )


def headings(md: str) -> list[dict]:
    """Table of contents (h2/h3 in document order); ids are assigned client-side by index."""
    toks = _md.parse(md)
    return [
        {"level": 3 if t.tag == "h3" else 2, "text": _inline_text(toks[i + 1])}
        for i, t in enumerate(toks)
        if t.type == "heading_open" and t.tag in ("h1", "h2", "h3")
    ]


def plain_text(md: str) -> str:
    """Readable text without markup (for excerpts and word counts)."""
    parts = [_inline_text(t) for t in _md.parse(md) if t.type == "inline"]
    return " ".join(" ".join(parts).split())
