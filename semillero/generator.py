"""Seed URL generation for Semillero."""

from .utils import normalize_domain


def generate_seed_urls(value: str) -> list[str]:
    """Generate basic HTTP and HTTPS seed URLs for a domain."""
    domain = normalize_domain(value)
    base_domain = domain.removeprefix("www.")

    return [
        f"https://{base_domain}",
        f"http://{base_domain}",
        f"https://www.{base_domain}",
        f"http://www.{base_domain}",
    ]