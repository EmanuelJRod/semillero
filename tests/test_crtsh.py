"""Tests for the crt.sh domain source."""

import json
from io import BytesIO
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

from semillero.sources import crtsh


class FakeResponse:
    """Minimal context-managed HTTP response for tests."""

    def __init__(self, payload: object) -> None:
        self._body = BytesIO(json.dumps(payload).encode("utf-8"))

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        """Return the encoded response body."""
        return self._body.read()


def test_parse_response_normalizes_deduplicates_and_sorts_names() -> None:
    """Normalize valid names, including multiline and wildcard values."""
    payload = [
        {
            "name_value": (
                "WWW.Example.com\n*.api.example.com\napi.example.com.\n"
                "other.test\nnot a domain"
            ),
            "common_name": "example.com",
        },
        {"name_value": "shop.example.com"},
    ]

    assert crtsh.parse_response(payload, "example.com") == [
        "api.example.com",
        "example.com",
        "shop.example.com",
        "www.example.com",
    ]


def test_parse_response_rejects_unexpected_top_level_format() -> None:
    """Reject a response that is not a list of certificate records."""
    with pytest.raises(crtsh.CrtshError, match="unexpected response format"):
        crtsh.parse_response({"name_value": "example.com"}, "example.com")


def test_collect_domains_queries_crtsh(monkeypatch: pytest.MonkeyPatch) -> None:
    """Build the expected API request and process its JSON response."""
    captured_request: Request | None = None
    captured_timeout: float | None = None

    def fake_urlopen(request: Request, timeout: float) -> FakeResponse:
        nonlocal captured_request, captured_timeout
        captured_request = request
        captured_timeout = timeout
        return FakeResponse([{"name_value": "*.example.com\nwww.example.com"}])

    monkeypatch.setattr(crtsh, "urlopen", fake_urlopen)

    assert crtsh.collect_domains("HTTPS://Example.COM/path") == [
        "example.com",
        "www.example.com",
    ]
    assert captured_request is not None
    assert captured_request.full_url == (
        "https://crt.sh/?q=%25.example.com&output=json"
    )
    assert captured_timeout == crtsh.DEFAULT_TIMEOUT


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (URLError("connection failed"), "Could not connect to crt.sh"),
        (
            HTTPError("https://crt.sh/", 503, "Unavailable", {}, None),
            "crt.sh returned HTTP 503",
        ),
        (TimeoutError(), "The request to crt.sh timed out"),
    ],
)
def test_collect_domains_handles_request_errors(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    message: str,
) -> None:
    """Convert network and HTTP failures into source-specific errors."""
    def fake_urlopen(request: Request, timeout: float) -> FakeResponse:
        raise error

    monkeypatch.setattr(crtsh, "urlopen", fake_urlopen)

    with pytest.raises(crtsh.CrtshError, match=message):
        crtsh.collect_domains("example.com")


def test_collect_domains_rejects_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Report a response body that is not valid JSON."""
    class InvalidJsonResponse(FakeResponse):
        def __init__(self) -> None:
            self._body = BytesIO(b"not json")

    monkeypatch.setattr(
        crtsh,
        "urlopen",
        lambda request, timeout: InvalidJsonResponse(),
    )

    with pytest.raises(crtsh.CrtshError, match="invalid JSON"):
        crtsh.collect_domains("example.com")
