"""The sanitizer is the security boundary for article bodies."""

from html.parser import HTMLParser

import pytest

from app.services import markdown

ATTACKS = [
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    "[click](javascript:alert(1))",
    "[click](JaVaScRiPt:alert(1))",
    "[click](data:text/html;base64,PHNjcmlwdD4=)",
    "<iframe src='https://evil.example'></iframe>",
    "<a href='javascript:alert(1)' onclick='x()'>x</a>",
    "<svg onload=alert(1)></svg>",
    "![x](javascript:alert(1))",
    "<style>body{display:none}</style>",
    "<form action=https://evil.example><input></form>",
]


class _Audit(HTMLParser):
    """Collect every tag and attribute the output would give a browser."""

    def __init__(self):
        super().__init__()
        self.found: list[tuple[str, dict]] = []

    def handle_starttag(self, tag, attrs):
        self.found.append((tag, dict(attrs)))


@pytest.mark.parametrize("attack", ATTACKS)
def test_attacks_are_neutralised(attack):
    audit = _Audit()
    audit.feed(markdown.render(attack))
    for tag, attrs in audit.found:
        assert tag in markdown.TAGS
        assert set(attrs) <= markdown.ATTRS.get(tag, set()) | {"rel"}
        for url in (attrs.get("href"), attrs.get("src")):
            assert url is None or url.split(":")[0] in ("http", "https", "mailto")


def test_links_get_rel_and_keep_https():
    html = markdown.render("[ok](https://example.org/a?b=1)")
    assert 'href="https://example.org/a?b=1"' in html
    assert 'rel="noopener nofollow ugc"' in html


def test_author_supplied_rel_and_target_are_overwritten():
    # Raw HTML is escaped to text, so the only <a> that exists is the Markdown one.
    html = markdown.render(
        '<a href="https://x.org" rel="opener" target="_blank">x</a> [y](https://y.org)'
    )
    audit = _Audit()
    audit.feed(html)
    assert [a for t, a in audit.found if t == "a"] == [
        {"href": "https://y.org", "rel": "noopener nofollow ugc"}
    ]


def test_formatting_survives():
    html = markdown.render(
        "# Big\n\n**bold** _it_ `code`\n\n- a\n- b\n\n> quote\n\n| a | b |\n|---|---|\n| 1 | 2 |"
    )
    for tag in (
        "<h2>",
        "<strong>",
        "<em>",
        "<code>",
        "<li>",
        "<blockquote>",
        "<table>",
    ):
        assert tag in html  # h1 is demoted to h2


def test_toc_and_plain_text():
    md = "# One\n\ntext *here*\n\n## Two\n\n### Three `x`\n\n#### Four"
    assert markdown.headings(md) == [
        {"level": 2, "text": "One"},
        {"level": 2, "text": "Two"},
        {"level": 3, "text": "Three x"},
    ]
    assert markdown.plain_text(md).startswith("One text here Two")


def test_azerbaijani_and_french_text_passes_through():
    html = markdown.render("Əlifba: ə ı ş ç ğ ö ü — « é è ê à œ »")
    assert "Əlifba" in html and "œ" in html
