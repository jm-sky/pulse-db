"""Unit tests for SSRF-safe remote URL helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.core.http_ssrf import (
    SafeHttpUrl,
    UnsafeRemoteUrlError,
    download_safe_http_url,
    prepare_safe_http_url,
)


def _fake_addrinfo(ip: str, family: int = 2) -> list:
    # family 2 = AF_INET
    return [(family, 0, 0, "", (ip, 0))]


def test_rejects_non_http_scheme() -> None:
    with pytest.raises(UnsafeRemoteUrlError, match="HTTP and HTTPS"):
        prepare_safe_http_url("ftp://example.com/a.png")


def test_rejects_localhost_hostname() -> None:
    with pytest.raises(UnsafeRemoteUrlError, match="Localhost"):
        prepare_safe_http_url("http://localhost/a.png")


def test_rejects_literal_private_ip() -> None:
    with pytest.raises(UnsafeRemoteUrlError, match="Non-public"):
        prepare_safe_http_url("http://10.0.0.1/a.png")


def test_rejects_loopback_hostname_literal() -> None:
    with pytest.raises(UnsafeRemoteUrlError, match="Localhost|Non-public"):
        prepare_safe_http_url("http://127.0.0.1/a.png")


def test_rejects_link_local_metadata_ip() -> None:
    with pytest.raises(UnsafeRemoteUrlError, match="Non-public"):
        prepare_safe_http_url("http://169.254.169.254/latest/meta-data/")


def test_rejects_private_resolved_ip() -> None:
    with patch("app.core.http_ssrf.socket.getaddrinfo", return_value=_fake_addrinfo("10.0.0.5")):
        with pytest.raises(UnsafeRemoteUrlError, match="Non-public"):
            prepare_safe_http_url("https://evil.example/a.png")


def test_canonicalizes_and_strips_userinfo() -> None:
    with patch("app.core.http_ssrf.socket.getaddrinfo", return_value=_fake_addrinfo("93.184.216.34")):
        safe = prepare_safe_http_url("https://user:pass@Example.COM:443/path/img.png?x=1#frag")
    assert safe.canonical_url == "https://example.com/path/img.png?x=1"
    assert safe.hostname == "example.com"
    assert safe.port == 443
    assert safe.pinned_ip == "93.184.216.34"
    assert "user" not in safe.canonical_url
    assert safe.host_header == "example.com"


def test_pinned_url_uses_ip() -> None:
    safe = SafeHttpUrl(
        canonical_url="http://example.com/a.png",
        scheme="http",
        hostname="example.com",
        port=80,
        pinned_ip="93.184.216.34",
    )
    assert safe.pinned_url == "http://93.184.216.34:80/a.png"


@pytest.mark.asyncio
async def test_download_http_uses_pinned_url_and_host_header() -> None:
    from unittest.mock import AsyncMock

    safe = SafeHttpUrl(
        canonical_url="http://example.com/a.png",
        scheme="http",
        hostname="example.com",
        port=80,
        pinned_ip="93.184.216.34",
    )

    mock_response = MagicMock()
    mock_response.content = b"img"
    mock_response.raise_for_status = MagicMock()

    calls: list[tuple] = []

    async def capturing_get(url, headers=None):
        calls.append((url, headers))
        return mock_response

    mock_client = AsyncMock()
    mock_client.get = capturing_get
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False

    with (
        patch("app.core.http_ssrf.socket.getaddrinfo", return_value=_fake_addrinfo("93.184.216.34")),
        patch("app.core.http_ssrf.httpx.AsyncClient", return_value=mock_client) as client_cls,
    ):
        content = await download_safe_http_url(safe, timeout=5.0)

    assert content == b"img"
    assert calls[0][0] == "http://93.184.216.34:80/a.png"
    assert calls[0][1]["Host"] == "example.com"
    _, kwargs = client_cls.call_args
    assert kwargs.get("follow_redirects") is False
