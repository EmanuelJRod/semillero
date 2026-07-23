"""Domain collection from the Cert Spotter certificate search API."""

import json
from json import JSONDecodeError
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..utils import is_valid_domain, normalize_domain

API_URL = "https://api.certspotter.com/v1/issuances"
DEFAULT_TIMEOUT = 15.0


class CertSpotterError(RuntimeError):
    """Raised when Cert Spotter cannot return a usable response."""


def parse_response(payload: object, domain: str) -> tuple[list[str], str | None]:
    """Extract normalized names and the last issuance ID from one page."""
    if not isinstance(payload, list):
        raise CertSpotterError(
            "Cert Spotter returned an unexpected response format."
        )

    names: set[str] = set()

    for issuance in payload:
        if not isinstance(issuance, dict):
            continue

        dns_names = issuance.get("dns_names")
        if not isinstance(dns_names, list):
            continue

        for raw_name in dns_names:
            if not isinstance(raw_name, str):
                continue

            name = raw_name.strip().lower().rstrip(".")
            if name.startswith("*."):
                name = name[2:]

            if (
                is_valid_domain(name)
                and (name == domain or name.endswith(f".{domain}"))
            ):
                names.add(name)

    last_id = None
    if payload:
        last_entry = payload[-1]
        if not isinstance(last_entry, dict) or not isinstance(
            last_entry.get("id"), str
        ):
            raise CertSpotterError(
                "Cert Spotter returned a page without a valid issuance ID."
            )
        last_id = last_entry["id"]

    return sorted(names), last_id


def _fetch_page(url: str, timeout: float) -> object:
    """Request and decode one page from Cert Spotter."""
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
        raise CertSpotterError(
            f"Cert Spotter returned HTTP {error.code}."
        ) from error
    except URLError as error:
        raise CertSpotterError(
            f"Could not connect to Cert Spotter: {error.reason}."
        ) from error
    except TimeoutError as error:
        raise CertSpotterError("The request to Cert Spotter timed out.") from error
    except UnicodeDecodeError as error:
        raise CertSpotterError(
            "Cert Spotter returned a response that is not valid UTF-8."
        ) from error

    try:
        return json.loads(body)
    except JSONDecodeError as error:
        raise CertSpotterError("Cert Spotter returned invalid JSON.") from error


def collect_domains(value: str, timeout: float = DEFAULT_TIMEOUT) -> list[str]:
    """Query Cert Spotter and return unique domain names for a target."""
    domain = normalize_domain(value)
    if not is_valid_domain(domain):
        raise ValueError(f"Invalid domain: {value}")

    parameters = {
        "domain": domain,
        "include_subdomains": "true",
        "expand": "dns_names",
    }
    names: set[str] = set()
    previous_id = None

    while True:
        url = f"{API_URL}?{urlencode(parameters)}"
        payload = _fetch_page(url, timeout)
        page_names, last_id = parse_response(payload, domain)
        names.update(page_names)

        if last_id is None:
            break
        if last_id == previous_id:
            raise CertSpotterError(
                "Cert Spotter returned a repeated pagination ID."
            )

        previous_id = last_id
        parameters["after"] = last_id

    return sorted(names)
