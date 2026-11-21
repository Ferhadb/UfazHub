"""Canonical URL normalization: two spellings of one link must collide in duplicate detection."""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING = {"fbclid", "gclid", "igshid", "mc_cid", "mc_eid", "ref", "ref_src", "si"}


def canonical_url(raw: str) -> str:
    """Return the canonical https form or raise ValueError (non-http scheme, credentials, no host)."""
    parts = urlsplit(raw.strip())
    if parts.scheme.lower() not in ("http", "https"):
        raise ValueError("Only http and https links are allowed")
    if parts.username or parts.password:
        raise ValueError("Links must not contain credentials")
    try:
        host = (parts.hostname or "").encode("idna").decode().lower()
        port = parts.port
    except (UnicodeError, ValueError) as exc:
        raise ValueError("Invalid link") from exc
    if not host or "." not in host:
        raise ValueError("Invalid link")
    host = host.removeprefix("www.")
    netloc = host if port in (None, 80, 443) else f"{host}:{port}"
    query = sorted(
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in _TRACKING
    )
    path = parts.path.rstrip("/") or "/"
    return urlunsplit(("https", netloc, path, urlencode(query), ""))
