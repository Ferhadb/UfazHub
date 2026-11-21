"""SSRF guard for server-side fetches of user-supplied URLs.

Two layers: `assert_public_url` checks scheme, port and every resolved address before each hop
(so each redirect target is re-checked), and `guarded_client` also validates at connect time,
which closes the DNS-rebinding gap between "check" and "connect".
"""

import asyncio
import ipaddress
import socket

import httpcore
import httpx

MAX_REDIRECTS = 3
NAT64 = ipaddress.ip_network("64:ff9b::/96")


class BlockedUrl(Exception):
    pass


def is_public(addr: str) -> bool:
    ip = ipaddress.ip_address(addr.split("%")[0])  # strip an IPv6 zone id
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        elif ip in NAT64:
            ip = ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)
    return ip.is_global and not (ip.is_multicast or ip.is_reserved or ip.is_unspecified)


async def _resolve(host: str, port: int) -> list[str]:
    infos = await asyncio.get_running_loop().getaddrinfo(
        host, port, type=socket.SOCK_STREAM
    )
    return [str(info[4][0]) for info in infos]


async def resolve_public(host: str, port: int) -> list[str]:
    """Resolve `host` and return its addresses, raising BlockedUrl unless ALL are public."""
    try:
        addrs = await _resolve(host, port)
    except OSError as exc:
        raise BlockedUrl(f"cannot resolve {host}") from exc
    if not addrs or not all(is_public(a) for a in addrs):
        raise BlockedUrl(f"{host} resolves to a non-public address")
    return addrs


async def assert_public_url(url: str) -> None:
    parts = httpx.URL(url)
    if parts.scheme not in ("http", "https") or not parts.host:
        raise BlockedUrl("only http(s) URLs are fetched")
    port = parts.port or (443 if parts.scheme == "https" else 80)
    if port not in (80, 443):
        raise BlockedUrl("only ports 80 and 443 are fetched")
    await resolve_public(parts.host, port)


class _GuardedBackend(httpcore.AnyIOBackend):
    async def connect_tcp(self, host, port, timeout=None, local_address=None, **kw):
        ip = (await resolve_public(host, port))[0]
        return await super().connect_tcp(ip, port, timeout, local_address, **kw)


def guarded_client(timeout: float = 5.0) -> httpx.AsyncClient:
    transport = httpx.AsyncHTTPTransport()
    # shortcut: httpx has no public hook for the network backend; re-check on httpx upgrades
    # (tests/test_ssrf.py connects to a real loopback server and must be refused).
    transport._pool._network_backend = _GuardedBackend()
    return httpx.AsyncClient(
        transport=transport,
        follow_redirects=False,
        trust_env=False,  # an env proxy would bypass the guard
        timeout=httpx.Timeout(timeout),
        headers={"User-Agent": "UFAZHubPreview/1.0"},
    )
