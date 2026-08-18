"""Tests for the AlienVault OTX domain source."""

import json
from http.client import RemoteDisconnected
from io import BytesIO
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

from semillero.sources import alienvault


class FakeResponse:
    """Minimal context-managed HTTP response for tests."""

    def __init__(self, body: str) -> None:
        self._body = BytesIO(body.encode("utf-8"))

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        """Return the encoded response body."""
        return self._body.read()


def test_collect_domains_normalizes_filters_deduplicates_and_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return only unique normalized hostnames within the target domain."""
    payload = {
        "passive_dns": [
            {"hostname": "Example.COM."},
            {"hostname": "WWW.Example.COM"},
            {"hostname": "www.example.com"},
            {"hostname": "api.example.com"},
            {"hostname": "example.net"},
            {"hostname": "notexample.com"},
            {"hostname": "fooexample.com"},
            {"hostname": "not a domain"},
        ],
        "has_next": False,
    }
    requested_urls: list[str] = []

    def fake_urlopen(request: Request, timeout: float) -> FakeResponse:
        requested_urls.append(request.full_url)
        assert timeout == alienvault.DEFAULT_TIMEOUT
        return FakeResponse(json.dumps(payload))

    monkeypatch.setattr(alienvault, "urlopen", fake_urlopen)

    assert alienvault.collect_domains("HTTPS://Example.COM/path", 2) == [
        "api.example.com",
        "example.com",
    ]
    assert requested_urls == [
        f"{alienvault.API_URL}/example.com/passive_dns?page=1&limit=2"
    ]


def test_collect_domains_follows_pagination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Request another page when AlienVault reports more results."""
    responses = iter(
        [
            FakeResponse(
                json.dumps(
                    {
                        "passive_dns": [{"hostname": "one.example.com"}],
                        "has_next": True,
                    }
                )
            ),
            FakeResponse(
                json.dumps(
                    {
                        "passive_dns": [{"hostname": "two.example.com"}],
                        "has_next": False,
                    }
                )
            ),
        ]
    )
    requested_urls: list[str] = []

    def fake_urlopen(request: Request, timeout: float) -> FakeResponse:
        requested_urls.append(request.full_url)
        return next(responses)

    monkeypatch.setattr(alienvault, "urlopen", fake_urlopen)

    assert alienvault.collect_domains("example.com", 2) == [
        "one.example.com",
        "two.example.com",
    ]
    assert "page=1" in requested_urls[0]
    assert "page=2" in requested_urls[1]


def test_collect_domains_returns_empty_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return an empty collection for a valid response without records."""
    monkeypatch.setattr(
        alienvault,
        "urlopen",
        lambda request, timeout: FakeResponse(
            json.dumps({"passive_dns": [], "has_next": False})
        ),
    )

    assert alienvault.collect_domains("example.com", 10) == []


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (URLError("connection failed"), "Could not connect to AlienVault OTX"),
        (
            HTTPError("https://otx.alienvault.com/", 429, "Limited", {}, None),
            "AlienVault OTX returned HTTP 429",
        ),
        (
            HTTPError("https://otx.alienvault.com/", 502, "Bad Gateway", {}, None),
            "AlienVault OTX returned HTTP 502",
        ),
        (TimeoutError(), "The request to AlienVault OTX timed out"),
        (
            RemoteDisconnected(
                "Remote end closed connection without response"
            ),
            "Remote end closed connection without response",
        ),
    ],
)
def test_collect_domains_handles_request_errors(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    message: str,
) -> None:
    """Convert transport failures into source-specific errors."""
    def fake_urlopen(request: Request, timeout: float) -> FakeResponse:
        raise error

    monkeypatch.setattr(alienvault, "urlopen", fake_urlopen)

    with pytest.raises(alienvault.AlienVaultError, match=message):
        alienvault.collect_domains("example.com", 10)


def test_collect_domains_rejects_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Convert malformed JSON into a source-specific error."""
    monkeypatch.setattr(
        alienvault,
        "urlopen",
        lambda request, timeout: FakeResponse("not json"),
    )

    with pytest.raises(alienvault.AlienVaultError, match="invalid JSON"):
        alienvault.collect_domains("example.com", 10)


@pytest.mark.parametrize(
    "payload",
    [None, [], {}, {"passive_dns": None}, {"passive_dns": [], "has_next": 1}],
)
def test_collect_domains_rejects_unexpected_response_format(
    monkeypatch: pytest.MonkeyPatch,
    payload: object,
) -> None:
    """Reject valid JSON with an unexpected response structure."""
    monkeypatch.setattr(
        alienvault,
        "urlopen",
        lambda request, timeout: FakeResponse(json.dumps(payload)),
    )

    with pytest.raises(alienvault.AlienVaultError, match="unexpected"):
        alienvault.collect_domains("example.com", 10)
