"""Tests for seed URL generation."""

import pytest

from semillero.generator import generate_seed_urls


def test_generate_seed_urls_from_domain() -> None:
    """Generate HTTP and HTTPS seeds from a plain domain."""
    assert generate_seed_urls("example.com") == [
        "https://example.com",
        "http://example.com",
        "https://www.example.com",
        "http://www.example.com",
    ]


def test_generate_seed_urls_from_full_url() -> None:
    """Normalize a complete URL before generating seeds."""
    assert generate_seed_urls("https://WWW.Example.ORG/some/path") == [
        "https://example.org",
        "http://example.org",
        "https://www.example.org",
        "http://www.example.org",
    ]


def test_generate_seed_urls_does_not_duplicate_www() -> None:
    """Avoid producing domains with duplicated www prefixes."""
    assert generate_seed_urls("www.example.com") == [
        "https://example.com",
        "http://example.com",
        "https://www.example.com",
        "http://www.example.com",
    ]


def test_generate_seed_urls_rejects_empty_value() -> None:
    """Reject an empty domain value."""
    with pytest.raises(ValueError, match="Domain cannot be empty"):
        generate_seed_urls("")