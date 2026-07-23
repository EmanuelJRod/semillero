"""Tests for the Common Crawl URL source."""

import json
from io import BytesIO
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

from semillero.sources import commoncrawl


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


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (".AR", ".ar"),
        ("nz", ".nz"),
        (".com.ar", ".com.ar"),
    ],
)
def test_normalize_suffix(value: str, expected: str) -> None:
    """Normalize supported domain suffix forms."""
    assert commoncrawl.normalize_suffix(value) == expected


@pytest.mark.parametrize("value", ["", ".", ".bad_suffix", ".-ar"])
def test_normalize_suffix_rejects_invalid_values(value: str) -> None:
    """Reject malformed domain suffixes."""
    with pytest.raises(ValueError):
        commoncrawl.normalize_suffix(value)


def test_parse_records_normalizes_filters_and_deduplicates_urls() -> None:
    """Extract one HTTP URL per matching hostname."""
    records = "\n".join(
        [
            json.dumps({"url": "HTTPS://WWW.Example.AR/path#fragment"}),
            json.dumps({"url": "https://www.example.ar/path"}),
            json.dumps({"url": "https://www.example.ar/another-path"}),
            json.dumps({"url": "http://www.example.ar/older-path"}),
            json.dumps({"url": "http://other.ar"}),
            json.dumps(
                {"url": "https://user:password@secure.ar:8443/path?query=value"}
            ),
            json.dumps({"url": "https://example.nz/"}),
            json.dumps({"url": "ftp://files.example.ar/data"}),
            json.dumps({"not_url": "https://ignored.ar/"}),
        ]
    )

    assert commoncrawl.parse_records(records, ".ar") == [
        "http://other.ar/",
        "https://secure.ar/",
        "https://www.example.ar/",
    ]


def test_collect_urls_uses_latest_index_and_random_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Query a random page from the latest Common Crawl index."""
    requested_urls: list[str] = []
    responses = iter(
        [
            FakeResponse(
                json.dumps(
                    [
                        {
                            "cdx-api": (
                                "https://index.commoncrawl.org/"
                                "CC-MAIN-2026-25-index"
                            )
                        }
                    ]
                )
            ),
            FakeResponse(json.dumps({"pages": 12})),
            FakeResponse(
                "\n".join(
                    json.dumps({"url": f"https://site-{number}.ar/"})
                    for number in range(100)
                )
            ),
        ]
    )

    def fake_urlopen(request: Request, timeout: float) -> FakeResponse:
        requested_urls.append(request.full_url)
        assert timeout == commoncrawl.DEFAULT_TIMEOUT
        return next(responses)

    monkeypatch.setattr(commoncrawl, "urlopen", fake_urlopen)
    def fake_sample(population: object, limit: int) -> list[object]:
        if isinstance(population, range):
            return [7, 8, 9, 10, 11][:limit]
        return list(population)[:limit]

    monkeypatch.setattr(commoncrawl.random, "sample", fake_sample)

    assert commoncrawl.collect_urls(".ar", 3) == [
        "https://site-0.ar/",
        "https://site-1.ar/",
        "https://site-10.ar/",
    ]
    assert requested_urls[0] == commoncrawl.CATALOG_URL
    assert "url=%2A.ar" in requested_urls[1]
    assert "showNumPages=true" in requested_urls[1]
    assert "page=7" in requested_urls[2]
    assert "limit=100" in requested_urls[2]
    assert "filter=status%3A200" in requested_urls[2]
    assert "filter=mime%3Atext%2Fhtml" in requested_urls[2]


def test_collect_urls_tries_another_page_for_distinct_hosts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Query another random page when one hostname dominates the first."""
    responses = iter(
        [
            FakeResponse(
                json.dumps(
                    [
                        {
                            "cdx-api": (
                                "https://index.commoncrawl.org/"
                                "CC-MAIN-2026-25-index"
                            )
                        }
                    ]
                )
            ),
            FakeResponse(json.dumps({"pages": 2})),
            FakeResponse(
                "\n".join(
                    [
                        json.dumps({"url": "https://one.ar/path-a"}),
                        json.dumps({"url": "https://one.ar/path-b"}),
                    ]
                )
            ),
            FakeResponse(json.dumps({"url": "https://two.ar/path"})),
        ]
    )

    monkeypatch.setattr(
        commoncrawl,
        "urlopen",
        lambda request, timeout: next(responses),
    )

    def fake_sample(population: object, limit: int) -> list[object]:
        if isinstance(population, range):
            return [0, 1]
        return list(population)[:limit]

    monkeypatch.setattr(commoncrawl.random, "sample", fake_sample)

    assert commoncrawl.collect_urls(".ar", 2) == [
        "https://one.ar/",
        "https://two.ar/",
    ]


def test_collect_urls_returns_fewer_urls_than_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return every available URL when fewer than the limit are found."""
    responses = iter(
        [
            FakeResponse(
                json.dumps(
                    [
                        {
                            "cdx-api": (
                                "https://index.commoncrawl.org/"
                                "CC-MAIN-2026-25-index"
                            )
                        }
                    ]
                )
            ),
            FakeResponse(json.dumps({"pages": 1})),
            FakeResponse(
                "\n".join(
                    [
                        json.dumps({"url": "https://one.cba.gov.ar/path"}),
                        json.dumps({"url": "https://two.cba.gov.ar/other"}),
                    ]
                )
            ),
        ]
    )
    monkeypatch.setattr(
        commoncrawl,
        "urlopen",
        lambda request, timeout: next(responses),
    )
    monkeypatch.setattr(
        commoncrawl.random,
        "sample",
        lambda population, limit: list(population)[:limit],
    )

    assert commoncrawl.collect_urls(".cba.gov.ar", 10) == [
        "https://one.cba.gov.ar/",
        "https://two.cba.gov.ar/",
    ]


def test_collect_urls_reports_when_no_unique_urls_are_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Report an error when index records yield no valid URLs."""
    responses = iter(
        [
            FakeResponse(
                json.dumps(
                    [
                        {
                            "cdx-api": (
                                "https://index.commoncrawl.org/"
                                "CC-MAIN-2026-25-index"
                            )
                        }
                    ]
                )
            ),
            FakeResponse(json.dumps({"pages": 1})),
            FakeResponse(json.dumps({"url": "https://outside.example/"})),
        ]
    )
    monkeypatch.setattr(
        commoncrawl,
        "urlopen",
        lambda request, timeout: next(responses),
    )
    monkeypatch.setattr(
        commoncrawl.random,
        "sample",
        lambda population, limit: list(population)[:limit],
    )

    with pytest.raises(commoncrawl.CommonCrawlError, match="no unique URLs"):
        commoncrawl.collect_urls(".cba.gov.ar", 10)


@pytest.mark.parametrize("limit", [0, 101])
def test_collect_urls_rejects_limit_outside_range(limit: int) -> None:
    """Reject limits that could be empty or overload the public API."""
    with pytest.raises(ValueError, match="between 1 and 100"):
        commoncrawl.collect_urls(".ar", limit)


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (URLError("connection failed"), "Could not connect to Common Crawl"),
        (
            HTTPError("https://index.commoncrawl.org/", 503, "Busy", {}, None),
            "Common Crawl returned HTTP 503",
        ),
        (TimeoutError(), "The request to Common Crawl timed out"),
    ],
)
def test_collect_urls_handles_request_errors(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    message: str,
) -> None:
    """Convert request failures into source-specific errors."""
    def fake_urlopen(request: Request, timeout: float) -> FakeResponse:
        raise error

    monkeypatch.setattr(commoncrawl, "urlopen", fake_urlopen)

    with pytest.raises(commoncrawl.CommonCrawlError, match=message):
        commoncrawl.collect_urls(".ar", 1)
