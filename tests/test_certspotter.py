"""Tests for the Cert Spotter domain source."""

import json
from io import BytesIO
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

from semillero.sources import certspotter


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


def test_parse_response_normalizes_wildcards_and_filters_names() -> None:
    """Normalize valid in-scope DNS names from one issuance page."""
    payload = [
        {
            "id": "10",
            "dns_names": [
                "Example.COM",
                "*.API.example.com",
                "api.example.com.",
                "other.test",
                "not a domain",
            ],
        }
    ]

    assert certspotter.parse_response(payload, "example.com") == (
        ["api.example.com", "example.com"],
        "10",
    )


def test_parse_response_rejects_unexpected_format() -> None:
    """Reject a response that is not a list of issuance objects."""
    with pytest.raises(certspotter.CertSpotterError, match="unexpected"):
        certspotter.parse_response({"dns_names": []}, "example.com")


def test_parse_response_requires_last_issuance_id() -> None:
    """Require an ID to continue paginating a non-empty response."""
    with pytest.raises(certspotter.CertSpotterError, match="issuance ID"):
        certspotter.parse_response([{"dns_names": ["example.com"]}], "example.com")


def test_collect_domains_follows_pagination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Request pages until Cert Spotter returns an empty list."""
    requested_urls: list[str] = []
    responses = iter(
        [
            FakeResponse(
                [{"id": "10", "dns_names": ["www.example.com", "example.com"]}]
            ),
            FakeResponse(
                [{"id": "20", "dns_names": ["api.example.com", "example.com"]}]
            ),
            FakeResponse([]),
        ]
    )

    def fake_urlopen(request: Request, timeout: float) -> FakeResponse:
        requested_urls.append(request.full_url)
        assert timeout == certspotter.DEFAULT_TIMEOUT
        return next(responses)

    monkeypatch.setattr(certspotter, "urlopen", fake_urlopen)

    assert certspotter.collect_domains("HTTPS://Example.COM/path") == [
        "api.example.com",
        "example.com",
        "www.example.com",
    ]
    assert requested_urls == [
        (
            "https://api.certspotter.com/v1/issuances?"
            "domain=example.com&include_subdomains=true&expand=dns_names"
        ),
        (
            "https://api.certspotter.com/v1/issuances?"
            "domain=example.com&include_subdomains=true&expand=dns_names&after=10"
        ),
        (
            "https://api.certspotter.com/v1/issuances?"
            "domain=example.com&include_subdomains=true&expand=dns_names&after=20"
        ),
    ]


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (URLError("connection failed"), "Could not connect to Cert Spotter"),
        (
            HTTPError("https://api.certspotter.com/", 429, "Limited", {}, None),
            "Cert Spotter returned HTTP 429",
        ),
        (TimeoutError(), "The request to Cert Spotter timed out"),
    ],
)
def test_collect_domains_handles_request_errors(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    message: str,
) -> None:
    """Convert request failures into source-specific errors."""
    def fake_urlopen(request: Request, timeout: float) -> FakeResponse:
        raise error

    monkeypatch.setattr(certspotter, "urlopen", fake_urlopen)

    with pytest.raises(certspotter.CertSpotterError, match=message):
        certspotter.collect_domains("example.com")


def test_collect_domains_rejects_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Report a response body that is not valid JSON."""
    class InvalidJsonResponse(FakeResponse):
        def __init__(self) -> None:
            self._body = BytesIO(b"not json")

    monkeypatch.setattr(
        certspotter,
        "urlopen",
        lambda request, timeout: InvalidJsonResponse(),
    )

    with pytest.raises(certspotter.CertSpotterError, match="invalid JSON"):
        certspotter.collect_domains("example.com")
