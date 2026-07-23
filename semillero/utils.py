"""Utility functions for Semillero."""

import re
from urllib.parse import urlparse

_DOMAIN_PATTERN = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"
)


def normalize_domain(value: str) -> str:
    """Return a normalized domain without scheme, path, or trailing dot."""
    candidate = value.strip().lower()

    if not candidate:
        raise ValueError("Domain cannot be empty.")

    if "://" not in candidate:
        candidate = f"//{candidate}"

    parsed = urlparse(candidate)
    domain = parsed.hostname

    if domain is None:
        raise ValueError(f"Invalid domain: {value}")

    return domain.rstrip(".")


def is_valid_domain(value: str) -> bool:
    """Return whether a value has a valid DNS domain shape."""
    return _DOMAIN_PATTERN.fullmatch(value) is not None
