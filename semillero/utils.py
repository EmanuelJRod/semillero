"""Utility functions for Semillero."""

from urllib.parse import urlparse


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