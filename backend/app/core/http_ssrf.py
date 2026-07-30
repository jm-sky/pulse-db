"""Helpers to validate and fetch remote HTTP(S) URLs without SSRF footguns.

Used when the product intentionally accepts a user-provided public URL (e.g. image
import). Blocks non-global destinations, strips userinfo, disables redirects, and
pins the TCP connection to a DNS-resolved public IP (with correct Host/SNI).
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse

import httpx

logger = logging.getLogger(__name__)

BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
        "[::1]",
        "metadata.google.internal",
    }
)


class UnsafeRemoteUrlError(ValueError):
    """Raised when a URL fails SSRF checks."""


@dataclass(frozen=True, slots=True)
class SafeHttpUrl:
    """URL that passed SSRF checks, with a public IP to pin the connection to."""

    canonical_url: str
    scheme: str
    hostname: str
    port: int
    pinned_ip: str

    @property
    def host_header(self) -> str:
        default_port = 443 if self.scheme == "https" else 80
        if self.port == default_port:
            return self.hostname
        return f"{self.hostname}:{self.port}"

    @property
    def pinned_url(self) -> str:
        """Canonical URL with host replaced by the pinned IP (for TCP connect)."""
        parsed = urlparse(self.canonical_url)
        ip = self.pinned_ip
        if ":" in ip:
            netloc = f"[{ip}]:{self.port}"
        else:
            netloc = f"{ip}:{self.port}"
        return urlunparse((self.scheme, netloc, parsed.path, "", parsed.query, ""))


def _reject_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    """Raise if *ip* is not a safe public (global) destination."""
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified or not ip.is_global:
        raise UnsafeRemoteUrlError("Non-public IP addresses are not allowed")


def _resolve_public_ips(hostname: str) -> list[str]:
    try:
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeRemoteUrlError("Could not resolve hostname") from exc

    if not addr_info:
        raise UnsafeRemoteUrlError("Could not resolve hostname")

    public_ips: list[str] = []
    for family, _, _, _, sockaddr in addr_info:
        if family not in (socket.AF_INET, socket.AF_INET6):
            continue
        host = sockaddr[0]
        if not isinstance(host, str):
            continue
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            continue
        _reject_ip(ip)
        public_ips.append(host)

    if not public_ips:
        raise UnsafeRemoteUrlError("Could not resolve hostname to a public IP")
    return public_ips


def prepare_safe_http_url(url: str) -> SafeHttpUrl:
    """
    Validate *url* and return a canonical form pinned to a public resolved IP.

    Raises:
        UnsafeRemoteUrlError: if the URL is unsafe or invalid
    """
    try:
        parsed = urlparse(url)
    except Exception as exc:
        raise UnsafeRemoteUrlError("Invalid URL format") from exc

    if parsed.scheme == "https":
        scheme = "https"
        default_port = 443
    elif parsed.scheme == "http":
        scheme = "http"
        default_port = 80
    else:
        raise UnsafeRemoteUrlError("Only HTTP and HTTPS URLs are allowed")

    hostname = parsed.hostname
    if not hostname:
        raise UnsafeRemoteUrlError("Invalid URL format: missing hostname")

    hostname = hostname.lower()
    if hostname in BLOCKED_HOSTNAMES:
        raise UnsafeRemoteUrlError("Localhost URLs are not allowed")

    # Literal IP in the URL must also be public
    try:
        _reject_ip(ipaddress.ip_address(hostname))
    except ValueError:
        pass  # hostname is not a literal IP

    port = parsed.port or default_port
    public_ips = _resolve_public_ips(hostname)
    pinned_ip = public_ips[0]

    # Rebuild without userinfo / fragment
    if port == default_port:
        netloc = hostname
    else:
        netloc = f"{hostname}:{port}"

    path = parsed.path or "/"
    canonical = urlunparse((scheme, netloc, path, "", parsed.query, ""))

    return SafeHttpUrl(
        canonical_url=canonical,
        scheme=scheme,
        hostname=hostname,
        port=port,
        pinned_ip=pinned_ip,
    )


async def download_safe_http_url(safe: SafeHttpUrl, *, timeout: float = 15.0) -> bytes:
    """
    GET *safe* URL bytes, connecting to the pinned public IP with Host/SNI set
    to the original hostname. Redirects are disabled.
    """
    # Re-resolve immediately before connect to shrink DNS-rebinding window
    public_ips = _resolve_public_ips(safe.hostname)
    if safe.pinned_ip not in public_ips:
        pinned_ip = public_ips[0]
        safe = SafeHttpUrl(
            canonical_url=safe.canonical_url,
            scheme=safe.scheme,
            hostname=safe.hostname,
            port=safe.port,
            pinned_ip=pinned_ip,
        )

    headers = {"Host": safe.host_header}

    if safe.scheme == "http":
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            response = await client.get(safe.pinned_url, headers=headers)
            response.raise_for_status()
            return response.content

    # HTTPS: open TLS to pinned IP with SNI=hostname, then speak HTTP/1.1 via httpx
    # over a custom transport is complex; use httpx with a preconfigured SSL context
    # and URL that keeps the hostname for cert verification while forcing the peer IP
    # via an AsyncBaseTransport.
    transport = _PinnedIPTransport(safe.pinned_ip, safe.hostname)
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=False,
        transport=transport,
    ) as client:
        response = await client.get(safe.canonical_url, headers=headers)
        response.raise_for_status()
        return response.content


class _PinnedIPTransport(httpx.AsyncHTTPTransport):
    """HTTP transport that always connects to *pinned_ip* (SNI uses request host)."""

    def __init__(self, pinned_ip: str, server_hostname: str) -> None:
        super().__init__()
        self._pinned_ip = pinned_ip
        self._server_hostname = server_hostname

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        # Rewrite URL host to the pinned IP for the TCP connection; keep Host header
        # (set by caller) and set SNI via extensions when supported.
        pinned = request.url.copy_with(host=self._pinned_ip)
        extensions = dict(request.extensions or {})
        # httpcore uses `sni_hostname` in extensions for TLS
        extensions["sni_hostname"] = self._server_hostname
        pinned_request = httpx.Request(
            method=request.method,
            url=pinned,
            headers=request.headers,
            stream=request.stream,
            extensions=extensions,
        )
        return await super().handle_async_request(pinned_request)
