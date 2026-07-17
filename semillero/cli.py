"""Command-line interface for Semillero."""

import argparse

from .config import APP_NAME, VERSION


def _handle_version() -> None:
    """Print the application version."""
    print(f"{APP_NAME} {VERSION}")


def _build_parser() -> argparse.ArgumentParser:
    """Build and return the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog=APP_NAME.lower(),
        description="Generate seed URLs for .ar domain discovery workflows.",
    )
    subparsers = parser.add_subparsers(dest="command")

    version_parser = subparsers.add_parser(
        "version",
        help="Show the application version.",
    )
    version_parser.set_defaults(handler=_handle_version)

    return parser


def main() -> None:
    """Run the Semillero command-line interface."""
    parser = _build_parser()
    args = parser.parse_args()

    if hasattr(args, "handler"):
        args.handler()
    else:
        parser.print_help()
