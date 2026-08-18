"""Domain collection from AlienVault OTX passive DNS."""

import json
from http.client import RemoteDisconnected
from json import JSONDecodeError
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from ..utils import is_valid_domain, normalize_domain

API_URL = "https://otx.alienvault.com/api/v1/indicators/domain"
DEFAULT_TIMEOUT = 15.0
MAX_LIMIT = 100


class AlienVaultError(RuntimeError):
    """Raised when AlienVault OTX cannot return a usable response."""


def parse_response(payload: object, domain: str) -> tuple[list[str], bool]:
    """Extract normalized in-scope hostnames and pagination state."""
    if not isinstance(payload, dict) or not isinstance(
        payload.get("passive_dns"), list
    ):
        raise AlienVaultError(
            "AlienVault OTX returned an unexpected response format."
        )

    names: set[str] = set()
    for record in payload["passive_dns"]:
        if not isinstance(record, dict):
            continue

        raw_name = record.get("hostname")
        if not isinstance(raw_name, str):
            continue

        name = raw_name.strip().lower().rstrip(".")
        if (
            is_valid_domain(name)
            and (name == domain or name.endswith(f".{domain}"))
        ):
            names.add(name)

    has_next = payload.get("has_next", False)
    if not isinstance(has_next, bool):
        raise AlienVaultError(
            "AlienVault OTX returned an unexpected pagination format."
        )

    return sorted(names), has_next


def _fetch_page(url: str, timeout: float) -> object:
    """Request and decode one AlienVault OTX response page."""
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "Semillero/0.1",
        },
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except HTTPError as error:
        raise AlienVaultError(
            f"AlienVault OTX returned HTTP {error.code}."
        ) from error
    except URLError as error:
        raise AlienVaultError(
            f"Could not connect to AlienVault OTX: {error.reason}."
        ) from error
    except RemoteDisconnected as error:
        raise AlienVaultError(str(error)) from error
    except TimeoutError as error:
        raise AlienVaultError(
            "The request to AlienVault OTX timed out."
        ) from error
    except UnicodeDecodeError as error:
        raise AlienVaultError(
            "AlienVault OTX returned a response that is not valid UTF-8."
        ) from error

    try:
        return json.loads(body)
    except JSONDecodeError as error:
        raise AlienVaultError(
            "AlienVault OTX returned invalid JSON."
        ) from error


def collect_domains(
    value: str,
    limit: int,
    timeout: float = DEFAULT_TIMEOUT,
) -> list[str]:
    """Query AlienVault OTX and return unique hostnames for a target."""
    domain = normalize_domain(value)
    if not is_valid_domain(domain):
        raise ValueError(f"Invalid domain: {value}")
    if not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f"Limit must be between 1 and {MAX_LIMIT}.")

    names: set[str] = set()
    page = 1

    while len(names) < limit:
        parameters = urlencode({"page": page, "limit": limit})
        url = f"{API_URL}/{quote(domain, safe='')}/passive_dns?{parameters}"
        payload = _fetch_page(url, timeout)
        page_names, has_next = parse_response(payload, domain)
        names.update(page_names)

        if not has_next:
            break
        page += 1

    return sorted(names)[:limit]
