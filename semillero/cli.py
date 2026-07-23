"""Command-line interface for Semillero."""

import argparse

from .config import APP_NAME, VERSION
from .generator import generate_seed_urls


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

    return parser


def main() -> None:
    """Run the Semillero command-line interface."""
    parser = _build_parser()
    args = parser.parse_args()

    if hasattr(args, "handler"):
        args.handler(args)
    else:
        parser.print_help()