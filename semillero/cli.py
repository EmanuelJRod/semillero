"""Command-line interface for Semillero."""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .config import APP_NAME, VERSION
from .generator import generate_seed_urls
from .sources.alienvault import (
    AlienVaultError,
    collect_domains as collect_alienvault_domains,
)
from .sources.certspotter import (
    CertSpotterError,
    collect_domains as collect_certspotter_domains,
)
from .sources.commoncrawl import CommonCrawlError, collect_urls
from .sources.crtsh import CrtshError, collect_domains as collect_crtsh_domains


@dataclass(frozen=True)
class CollectSource:
    """Describe one source available to the collect command."""

    name: str
    help: str
    target_help: str
    collect: Callable[[str, int], list[str]]
    errors: tuple[type[Exception], ...]
    supports_limit: bool = False


def _collect_crtsh(target: str, _: int) -> list[str]:
    """Collect results from crt.sh."""
    return collect_crtsh_domains(target)


def _collect_certspotter(target: str, _: int) -> list[str]:
    """Collect results from Cert Spotter."""
    return collect_certspotter_domains(target)


def _collect_commoncrawl(target: str, limit: int) -> list[str]:
    """Collect results from Common Crawl."""
    return collect_urls(target, limit)


def _collect_alienvault(target: str, limit: int) -> list[str]:
    """Collect results from AlienVault OTX."""
    return collect_alienvault_domains(target, limit)


COLLECT_SOURCES = (
    CollectSource(
        name="crtsh",
        help="Collect domain names from crt.sh.",
        target_help="Domain used as the crt.sh search target.",
        collect=_collect_crtsh,
        errors=(CrtshError, ValueError),
    ),
    CollectSource(
        name="certspotter",
        help="Collect domain names from Cert Spotter.",
        target_help="Domain used as the Cert Spotter search target.",
        collect=_collect_certspotter,
        errors=(CertSpotterError, ValueError),
    ),
    CollectSource(
        name="commoncrawl",
        help="Collect random URLs observed by Common Crawl.",
        target_help="Domain suffix used as the search target, such as .ar.",
        collect=_collect_commoncrawl,
        errors=(CommonCrawlError, ValueError),
        supports_limit=True,
    ),
    CollectSource(
        name="alienvault",
        help="Collect domain names from AlienVault OTX.",
        target_help="Domain used as the AlienVault OTX search target.",
        collect=_collect_alienvault,
        errors=(AlienVaultError, ValueError),
        supports_limit=True,
    ),
)


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


def _collect_targets(args: argparse.Namespace) -> list[str]:
    """Return collect targets from the positional argument or an input file."""
    if args.input is None:
        return [args.target]

    try:
        lines = Path(args.input).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise SystemExit(f"Error: Could not read input file: {error}") from error

    return [line.strip() for line in lines if line.strip()]


def _collect_from_source(
    source: CollectSource,
    target: str,
    limit: int,
) -> list[str]:
    """Collect results for one target from one source."""
    return source.collect(target, limit)


def _handle_collect_source(args: argparse.Namespace) -> None:
    """Collect and print results from one source."""
    source: CollectSource = args.collect_source
    targets = _collect_targets(args)
    limit = getattr(args, "limit", 10)

    for target in targets:
        try:
            results = _collect_from_source(source, target, limit)
        except source.errors as error:
            if args.input is None:
                raise SystemExit(f"Error: {error}") from error
            print(f"Error [{source.name}] [{target}]: {error}", file=sys.stderr)
            continue

        for result in results:
            print(result)


def _collect_from_all_sources(
    target: str,
    limit: int,
    show_target: bool,
) -> set[str]:
    """Collect unique results for one target from every registered source."""
    results: set[str] = set()

    for source in COLLECT_SOURCES:
        try:
            results.update(_collect_from_source(source, target, limit))
        except source.errors as error:
            target_label = f" [{target}]" if show_target else ""
            print(f"Error [{source.name}]{target_label}: {error}", file=sys.stderr)

    return results


def _handle_collect_all(args: argparse.Namespace) -> None:
    """Collect and print unique results from every registered source."""
    for target in _collect_targets(args):
        results = _collect_from_all_sources(target, args.limit, args.input is not None)

        for result in sorted(results):
            print(result)


def _add_collect_input(
    parser: argparse.ArgumentParser,
    target_help: str,
) -> None:
    """Add mutually exclusive positional and file inputs to a collect parser."""
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("target", nargs="?", help=target_help)
    inputs.add_argument(
        "--input",
        metavar="FILE",
        help="Read one domain per line from a UTF-8 text file.",
    )


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

    for source in COLLECT_SOURCES:
        source_parser = collect_subparsers.add_parser(
            source.name,
            help=source.help,
        )
        _add_collect_input(source_parser, source.target_help)
        if source.supports_limit:
            source_parser.add_argument(
                "--limit",
                type=int,
                default=10,
                help="Number of URLs to return, from 1 to 100 (default: 10).",
            )
        source_parser.set_defaults(
            handler=_handle_collect_source,
            collect_source=source,
        )

    all_parser = collect_subparsers.add_parser(
        "all",
        help="Collect results from every available source.",
    )
    _add_collect_input(all_parser, "Domain used as the search target.")
    all_parser.set_defaults(handler=_handle_collect_all, limit=10)

    return parser


def main() -> None:
    """Run the Semillero command-line interface."""
    parser = _build_parser()
    args = parser.parse_args()

    if hasattr(args, "handler"):
        args.handler(args)
    else:
        parser.print_help()
