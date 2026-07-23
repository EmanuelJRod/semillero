"""Random URL collection from the Common Crawl index."""

import json
import random
import re
from json import JSONDecodeError
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

CATALOG_URL = "https://index.commoncrawl.org/collinfo.json"
DEFAULT_TIMEOUT = 30.0
MAX_LIMIT = 100
_CANDIDATE_MULTIPLIER = 20
_MINIMUM_CANDIDATES = 100
_MAX_PAGE_REQUESTS = 5
_SUFFIX_PATTERN = re.compile(
    r"^\.(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*"
    r"[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?$"
)


class CommonCrawlError(RuntimeError):
    """Raised when Common Crawl cannot return a usable response."""


def normalize_suffix(value: str) -> str:
    """Return a validated lowercase domain suffix with a leading dot."""
    suffix = value.strip().lower()
    if not suffix:
        raise ValueError("Domain suffix cannot be empty.")
    if not suffix.startswith("."):
        suffix = f".{suffix}"
    if _SUFFIX_PATTERN.fullmatch(suffix) is None:
        raise ValueError(f"Invalid domain suffix: {value}")
    return suffix


def _request_text(url: str, timeout: float) -> str:
    """Request a UTF-8 text response from Common Crawl."""
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "Semillero/0.1",
        },
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8")
    except HTTPError as error:
        raise CommonCrawlError(
            f"Common Crawl returned HTTP {error.code}."
        ) from error
    except URLError as error:
        raise CommonCrawlError(
            f"Could not connect to Common Crawl: {error.reason}."
        ) from error
    except TimeoutError as error:
        raise CommonCrawlError(
            "The request to Common Crawl timed out."
        ) from error
    except UnicodeDecodeError as error:
        raise CommonCrawlError(
            "Common Crawl returned a response that is not valid UTF-8."
        ) from error


def _parse_json(body: str) -> object:
    """Decode a JSON response from Common Crawl."""
    try:
        return json.loads(body)
    except JSONDecodeError as error:
        raise CommonCrawlError("Common Crawl returned invalid JSON.") from error


def _latest_index_url(timeout: float) -> str:
    """Return the API URL for the most recent Common Crawl index."""
    catalog = _parse_json(_request_text(CATALOG_URL, timeout))
    if not isinstance(catalog, list) or not catalog:
        raise CommonCrawlError(
            "Common Crawl returned an unexpected catalog format."
        )

    latest = catalog[0]
    if not isinstance(latest, dict):
        raise CommonCrawlError(
            "Common Crawl returned an unexpected catalog format."
        )

    index_url = latest.get("cdx-api")
    if not isinstance(index_url, str) or not index_url.startswith(
        "https://index.commoncrawl.org/"
    ):
        raise CommonCrawlError(
            "Common Crawl returned an invalid index URL."
        )
    return index_url


def _build_query(index_url: str, parameters: list[tuple[str, object]]) -> str:
    """Build a Common Crawl index query URL."""
    return f"{index_url}?{urlencode(parameters)}"


def _page_count(index_url: str, suffix: str, timeout: float) -> int:
    """Return the number of result pages for a domain suffix."""
    url = _build_query(
        index_url,
        [
            ("url", f"*{suffix}"),
            ("output", "json"),
            ("showNumPages", "true"),
            ("filter", "status:200"),
            ("filter", "mime:text/html"),
        ],
    )
    payload = _parse_json(_request_text(url, timeout))
    if not isinstance(payload, dict) or not isinstance(payload.get("pages"), int):
        raise CommonCrawlError(
            "Common Crawl returned an unexpected page count format."
        )

    pages = payload["pages"]
    if pages < 1:
        raise CommonCrawlError(
            f"Common Crawl has no observed URLs for {suffix}."
        )
    return pages


def parse_records(body: str, suffix: str) -> list[str]:
    """Extract one in-scope observed URL per hostname."""
    urls_by_hostname: dict[str, str] = {}

    for line in body.splitlines():
        if not line.strip():
            continue
        payload = _parse_json(line)
        if not isinstance(payload, dict) or not isinstance(
            payload.get("url"), str
        ):
            continue

        parsed = urlsplit(payload["url"])
        hostname = parsed.hostname
        if (
            parsed.scheme not in {"http", "https"}
            or hostname is None
            or not hostname.lower().endswith(suffix)
        ):
            continue

        normalized_hostname = hostname.lower()
        normalized = f"{parsed.scheme.lower()}://{normalized_hostname}/"
        current = urls_by_hostname.get(normalized_hostname)
        if current is None or (
            normalized.startswith("https://") and current.startswith("http://")
        ):
            urls_by_hostname[normalized_hostname] = normalized

    return sorted(urls_by_hostname.values())


def collect_urls(
    value: str,
    limit: int,
    timeout: float = DEFAULT_TIMEOUT,
) -> list[str]:
    """Return a random sample of recently observed URLs for a suffix."""
    suffix = normalize_suffix(value)
    if not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f"Limit must be between 1 and {MAX_LIMIT}.")

    index_url = _latest_index_url(timeout)
    pages = _page_count(index_url, suffix, timeout)
    candidate_limit = max(limit * _CANDIDATE_MULTIPLIER, _MINIMUM_CANDIDATES)
    candidates: set[str] = set()
    selected_pages = random.sample(
        range(pages),
        min(_MAX_PAGE_REQUESTS, pages),
    )

    for page in selected_pages:
        url = _build_query(
            index_url,
            [
                ("url", f"*{suffix}"),
                ("output", "json"),
                ("page", page),
                ("limit", candidate_limit),
                ("fl", "url"),
                ("filter", "status:200"),
                ("filter", "mime:text/html"),
                ("collapse", "urlkey"),
            ],
        )
        candidates.update(parse_records(_request_text(url, timeout), suffix))
        if len(candidates) >= limit:
            break

    if len(candidates) < limit:
        raise CommonCrawlError(
            f"Common Crawl returned only {len(candidates)} unique URLs "
            f"for {suffix}; requested {limit}."
        )

    return random.sample(sorted(candidates), limit)
