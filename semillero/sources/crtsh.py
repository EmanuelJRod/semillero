"""Domain collection from the crt.sh certificate transparency service."""

import json
from json import JSONDecodeError
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..utils import is_valid_domain, normalize_domain

API_URL = "https://crt.sh/"
DEFAULT_TIMEOUT = 10.0


class CrtshError(RuntimeError):
    """Raised when crt.sh cannot return a usable response."""


def parse_response(payload: object, domain: str) -> list[str]:
    """Extract normalized, in-scope domain names from a crt.sh response."""
    if not isinstance(payload, list):
        raise CrtshError("crt.sh returned an unexpected response format.")

    names: set[str] = set()

    for entry in payload:
        if not isinstance(entry, dict):
            continue

        for field in ("name_value", "common_name"):
            value = entry.get(field)
            if not isinstance(value, str):
                continue

            for raw_name in value.splitlines():
                name = raw_name.strip().lower().rstrip(".")
                if name.startswith("*."):
                    name = name[2:]

                if (
                    is_valid_domain(name)
                    and (name == domain or name.endswith(f".{domain}"))
                ):
                    names.add(name)

    return sorted(names)


def collect_domains(value: str, timeout: float = DEFAULT_TIMEOUT) -> list[str]:
    """Query crt.sh and return unique domain names for a target domain."""
    domain = normalize_domain(value)
    if not is_valid_domain(domain):
        raise ValueError(f"Invalid domain: {value}")

    query = urlencode({"q": f"%.{domain}", "output": "json"})
    request = Request(
        f"{API_URL}?{query}",
        headers={
            "Accept": "application/json",
            "User-Agent": "Semillero/0.1",
        },
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except HTTPError as error:
        raise CrtshError(f"crt.sh returned HTTP {error.code}.") from error
    except URLError as error:
        raise CrtshError(f"Could not connect to crt.sh: {error.reason}.") from error
    except TimeoutError as error:
        raise CrtshError("The request to crt.sh timed out.") from error
    except UnicodeDecodeError as error:
        raise CrtshError("crt.sh returned a response that is not valid UTF-8.") from error

    try:
        payload = json.loads(body)
    except JSONDecodeError as error:
        raise CrtshError("crt.sh returned invalid JSON.") from error

    return parse_response(payload, domain)
