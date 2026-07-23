"""Command-line interface for Semillero."""

import argparse

from .config import APP_NAME, VERSION
from .generator import generate_seed_urls
from .sources.certspotter import (
    CertSpotterError,
    collect_domains as collect_certspotter_domains,
)
from .sources.crtsh import CrtshError, collect_domains as collect_crtsh_domains


def _handle_version(_: argparse.Namespace) -> None:
    """Print the application version."""
    print(f"{APP_NAME} {VERSION}")


def _handle_generate(args: argparse.Namespace) -> None:
    """Generate basic seed URLs for a domain."""
    try:
        seed_urls = generate_seed_urls(args.domain)
    except ValueError as error:
        raise SystemExit(f"Error: {error}") from error

    for url in seed_urls:
        print(url)


def _handle_collect_crtsh(args: argparse.Namespace) -> None:
    """Collect domain names from crt.sh."""
    try:
        domains = collect_crtsh_domains(args.domain)
    except (CrtshError, ValueError) as error:
        raise SystemExit(f"Error: {error}") from error

    for domain in domains:
        print(domain)


def _handle_collect_certspotter(args: argparse.Namespace) -> None:
    """Collect domain names from Cert Spotter."""
    try:
        domains = collect_certspotter_domains(args.domain)
    except (CertSpotterError, ValueError) as error:
        raise SystemExit(f"Error: {error}") from error

    for domain in domains:
        print(domain)


def _build_parser() -> argparse.ArgumentParser:
    """Build and return the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog=APP_NAME.lower(),
        description="Generate seed URLs for domain discovery workflows.",
    )
    subparsers = parser.add_subparsers(dest="command")

    version_parser = subparsers.add_parser(
        "version",
        help="Show the application version.",
    )
    version_parser.set_defaults(handler=_handle_version)

    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate seed URLs for a domain.",
    )
    generate_parser.add_argument(
        "domain",
        help="Domain or URL used as the seed target.",
    )
    generate_parser.set_defaults(handler=_handle_generate)

    collect_parser = subparsers.add_parser(
        "collect",
        help="Collect domain names from an external source.",
    )
    collect_subparsers = collect_parser.add_subparsers(dest="source")

    crtsh_parser = collect_subparsers.add_parser(
        "crtsh",
        help="Collect domain names from crt.sh.",
    )
    crtsh_parser.add_argument(
        "domain",
        help="Domain used as the crt.sh search target.",
    )
    crtsh_parser.set_defaults(handler=_handle_collect_crtsh)

    certspotter_parser = collect_subparsers.add_parser(
        "certspotter",
        help="Collect domain names from Cert Spotter.",
    )
    certspotter_parser.add_argument(
        "domain",
        help="Domain used as the Cert Spotter search target.",
    )
    certspotter_parser.set_defaults(handler=_handle_collect_certspotter)

    return parser


def main() -> None:
    """Run the Semillero command-line interface."""
    parser = _build_parser()
    args = parser.parse_args()

    if hasattr(args, "handler"):
        args.handler(args)
    else:
        parser.print_help()
