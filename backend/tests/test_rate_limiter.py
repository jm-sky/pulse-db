"""Unit tests for rate-limiter client IP resolution.

Regression test for SEC-4 (pulse-db review, 2026-07-20): get_client_ip
trusted the leftmost (client-controlled) X-Forwarded-For entry, letting an
attacker send a fresh fake IP per request to dodge login/register limits.
We deploy behind exactly one trusted reverse proxy (Caddy), which appends
the real connecting IP as the last hop.
"""

from unittest.mock import MagicMock

from app.core.limiter import get_client_ip


def _request_with_headers(headers: dict[str, str]) -> MagicMock:
    request = MagicMock()
    request.headers = headers
    return request


def test_trusts_last_forwarded_for_hop_not_first() -> None:
    request = _request_with_headers({"X-Forwarded-For": "1.2.3.4, 9.9.9.9"})
    assert get_client_ip(request) == "9.9.9.9"


def test_attacker_spoofed_leading_hops_are_ignored() -> None:
    # An attacker can freely set arbitrary leading hops per request; only the
    # proxy-appended last hop should ever be trusted.
    request = _request_with_headers({"X-Forwarded-For": "10.0.0.1, 10.0.0.2, 10.0.0.3, 203.0.113.7"})
    assert get_client_ip(request) == "203.0.113.7"


def test_single_hop_forwarded_for() -> None:
    request = _request_with_headers({"X-Forwarded-For": "203.0.113.7"})
    assert get_client_ip(request) == "203.0.113.7"


def test_falls_back_to_real_ip_header() -> None:
    request = _request_with_headers({"X-Real-IP": "203.0.113.9"})
    assert get_client_ip(request) == "203.0.113.9"
