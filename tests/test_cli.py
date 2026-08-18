"""Tests for the Semillero command-line interface."""

import sys
from dataclasses import replace
from pathlib import Path

import pytest

from semillero import cli
from semillero.sources.alienvault import AlienVaultError
from semillero.sources.crtsh import CrtshError


def test_collect_crtsh_prints_collected_domains(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Print each domain returned by the crt.sh source."""
    monkeypatch.setattr(
        cli,
        "collect_crtsh_domains",
        lambda domain: ["example.com", "www.example.com"],
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["semillero", "collect", "crtsh", "example.com"],
    )

    cli.main()

    assert capsys.readouterr().out == "example.com\nwww.example.com\n"


def test_collect_crtsh_reports_source_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exit with a clear message when crt.sh collection fails."""
    def fail_collection(domain: str) -> list[str]:
        raise CrtshError("Could not connect to crt.sh.")

    monkeypatch.setattr(cli, "collect_crtsh_domains", fail_collection)
    monkeypatch.setattr(
        sys,
        "argv",
        ["semillero", "collect", "crtsh", "example.com"],
    )

    with pytest.raises(SystemExit, match="Error: Could not connect to crt.sh"):
        cli.main()


def test_collect_certspotter_prints_collected_domains(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Print each domain returned by the Cert Spotter source."""
    monkeypatch.setattr(
        cli,
        "collect_certspotter_domains",
        lambda domain: ["api.example.com", "example.com"],
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["semillero", "collect", "certspotter", "example.com"],
    )

    cli.main()

    assert capsys.readouterr().out == "api.example.com\nexample.com\n"


def test_collect_certspotter_reports_source_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exit with a clear message when Cert Spotter collection fails."""
    def fail_collection(domain: str) -> list[str]:
        raise cli.CertSpotterError("Cert Spotter returned HTTP 429.")

    monkeypatch.setattr(cli, "collect_certspotter_domains", fail_collection)
    monkeypatch.setattr(
        sys,
        "argv",
        ["semillero", "collect", "certspotter", "example.com"],
    )

    with pytest.raises(SystemExit, match="Error: Cert Spotter returned HTTP 429"):
        cli.main()


def test_collect_commoncrawl_prints_observed_urls(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Print each random URL returned by Common Crawl."""
    monkeypatch.setattr(
        cli,
        "collect_urls",
        lambda suffix, limit: ["https://one.ar/", "https://two.ar/"],
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["semillero", "collect", "commoncrawl", ".ar", "--limit", "2"],
    )

    cli.main()

    assert capsys.readouterr().out == "https://one.ar/\nhttps://two.ar/\n"


def test_collect_commoncrawl_reports_source_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exit with a clear message when Common Crawl collection fails."""
    def fail_collection(suffix: str, limit: int) -> list[str]:
        raise cli.CommonCrawlError("Common Crawl returned HTTP 503.")

    monkeypatch.setattr(cli, "collect_urls", fail_collection)
    monkeypatch.setattr(
        sys,
        "argv",
        ["semillero", "collect", "commoncrawl", ".ar"],
    )

    with pytest.raises(SystemExit, match="Error: Common Crawl returned HTTP 503"):
        cli.main()


def test_collect_alienvault_prints_collected_domains(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Dispatch AlienVault collection and print its results."""
    monkeypatch.setattr(
        cli,
        "collect_alienvault_domains",
        lambda domain, limit: ["api.example.com", "example.com"],
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["semillero", "collect", "alienvault", "example.com", "--limit", "2"],
    )

    cli.main()

    assert capsys.readouterr().out == "api.example.com\nexample.com\n"


def test_collect_alienvault_reports_source_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exit cleanly when AlienVault collection fails."""
    def fail_collection(domain: str, limit: int) -> list[str]:
        raise AlienVaultError("AlienVault OTX returned HTTP 500.")

    monkeypatch.setattr(cli, "collect_alienvault_domains", fail_collection)
    monkeypatch.setattr(
        sys,
        "argv",
        ["semillero", "collect", "alienvault", "example.com"],
    )

    with pytest.raises(SystemExit, match="AlienVault OTX returned HTTP 500"):
        cli.main()


def test_collect_all_runs_every_registered_source_and_deduplicates_results(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Run the complete registry and print each distinct result once."""
    called_sources: list[str] = []

    def collector_for(source_name: str) -> cli.CollectSource:
        source = next(
            source for source in cli.COLLECT_SOURCES if source.name == source_name
        )

        def collect(target: str, limit: int) -> list[str]:
            assert target == "example.com"
            assert limit == 10
            called_sources.append(source_name)
            return ["shared.example.com", f"{source_name}.example.com"]

        return replace(source, collect=collect)

    registered_sources = tuple(
        collector_for(source.name) for source in cli.COLLECT_SOURCES
    )
    monkeypatch.setattr(cli, "COLLECT_SOURCES", registered_sources)
    monkeypatch.setattr(
        sys,
        "argv",
        ["semillero", "collect", "all", "example.com"],
    )

    cli.main()

    output = capsys.readouterr()
    expected_results = {
        "shared.example.com",
        *(f"{source.name}.example.com" for source in registered_sources),
    }
    assert called_sources == [source.name for source in registered_sources]
    assert output.out.splitlines() == sorted(expected_results)
    assert output.err == ""


def test_collect_all_continues_after_a_source_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Report one source failure without interrupting later sources."""
    failed_source, successful_source = cli.COLLECT_SOURCES[:2]

    def fail_collection(target: str, limit: int) -> list[str]:
        raise ValueError("Source unavailable.")

    def collect_result(target: str, limit: int) -> list[str]:
        return ["result.example.com"]

    monkeypatch.setattr(
        cli,
        "COLLECT_SOURCES",
        (
            replace(failed_source, collect=fail_collection),
            replace(successful_source, collect=collect_result),
        ),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["semillero", "collect", "all", "example.com"],
    )

    cli.main()

    output = capsys.readouterr()
    assert output.out == "result.example.com\n"
    assert output.err == f"Error [{failed_source.name}]: Source unavailable.\n"


def test_collect_all_continues_when_alienvault_fails(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Preserve other results when AlienVault reports a source error."""
    alienvault_source = next(
        source for source in cli.COLLECT_SOURCES if source.name == "alienvault"
    )
    crtsh_source = next(
        source for source in cli.COLLECT_SOURCES if source.name == "crtsh"
    )

    def fail_alienvault(target: str, limit: int) -> list[str]:
        raise AlienVaultError("AlienVault OTX returned HTTP 500.")

    monkeypatch.setattr(
        cli,
        "COLLECT_SOURCES",
        (
            replace(
                crtsh_source,
                collect=lambda target, limit: ["www.example.com"],
            ),
            replace(alienvault_source, collect=fail_alienvault),
        ),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["semillero", "collect", "all", "example.com"],
    )

    cli.main()

    output = capsys.readouterr()
    assert output.out == "www.example.com\n"
    assert output.err == (
        "Error [alienvault]: AlienVault OTX returned HTTP 500.\n"
    )


def test_collect_all_preserves_alienvault_results_when_other_sources_fail(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Return AlienVault results after simultaneous failures elsewhere."""
    registered_sources: list[cli.CollectSource] = []
    for source in cli.COLLECT_SOURCES:
        if source.name == "alienvault":
            collect = lambda target, limit: ["api.example.com"]
        else:
            def collect(
                target: str,
                limit: int,
                source_name: str = source.name,
                error_type: type[Exception] = source.errors[0],
            ) -> list[str]:
                raise error_type(f"{source_name} unavailable.")

        registered_sources.append(replace(source, collect=collect))

    monkeypatch.setattr(cli, "COLLECT_SOURCES", tuple(registered_sources))
    monkeypatch.setattr(
        sys,
        "argv",
        ["semillero", "collect", "all", "example.com"],
    )

    cli.main()

    output = capsys.readouterr()
    assert output.out == "api.example.com\n"
    assert output.err.splitlines() == [
        f"Error [{source.name}]: {source.name} unavailable."
        for source in registered_sources
        if source.name != "alienvault"
    ]


def test_collect_source_reads_trimmed_non_empty_targets_from_file(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Process each non-empty trimmed line with an individual source."""
    monkeypatch.setattr(
        Path,
        "read_text",
        lambda path, encoding: (
            "  example.com  \n\n\texample.org\t\n   \nexample.net\n"
        ),
    )
    collected_targets: list[str] = []

    def collect_domains(target: str) -> list[str]:
        collected_targets.append(target)
        return [f"www.{target}"]

    monkeypatch.setattr(cli, "collect_crtsh_domains", collect_domains)
    monkeypatch.setattr(
        sys,
        "argv",
        ["semillero", "collect", "crtsh", "--input", "domains.txt"],
    )

    cli.main()

    output = capsys.readouterr()
    assert collected_targets == ["example.com", "example.org", "example.net"]
    assert output.out == (
        "www.example.com\nwww.example.org\nwww.example.net\n"
    )
    assert output.err == ""


def test_collect_all_processes_each_target_from_file(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Process every file target with every registered source."""
    monkeypatch.setattr(
        Path,
        "read_text",
        lambda path, encoding: "example.com\nexample.org\n",
    )
    calls: list[tuple[str, str]] = []

    def registered_collector(source: cli.CollectSource) -> cli.CollectSource:
        def collect(target: str, limit: int) -> list[str]:
            calls.append((source.name, target))
            return [f"{source.name}.{target}"]

        return replace(source, collect=collect)

    registered_sources = tuple(
        registered_collector(source) for source in cli.COLLECT_SOURCES
    )
    monkeypatch.setattr(cli, "COLLECT_SOURCES", registered_sources)
    monkeypatch.setattr(
        sys,
        "argv",
        ["semillero", "collect", "all", "--input", "domains.txt"],
    )

    cli.main()

    output = capsys.readouterr()
    assert calls == [
        (source.name, target)
        for target in ("example.com", "example.org")
        for source in registered_sources
    ]
    assert output.out.splitlines() == [
        *sorted(f"{source.name}.example.com" for source in registered_sources),
        *sorted(f"{source.name}.example.org" for source in registered_sources),
    ]
    assert output.err == ""


def test_collect_source_file_continues_after_target_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Keep processing file targets after one source error."""
    monkeypatch.setattr(
        Path,
        "read_text",
        lambda path, encoding: "invalid.example\nexample.com\n",
    )

    def collect_domains(target: str) -> list[str]:
        if target == "invalid.example":
            raise CrtshError("Source unavailable.")
        return [target]

    monkeypatch.setattr(cli, "collect_crtsh_domains", collect_domains)
    monkeypatch.setattr(
        sys,
        "argv",
        ["semillero", "collect", "crtsh", "--input", "domains.txt"],
    )

    cli.main()

    output = capsys.readouterr()
    assert output.out == "example.com\n"
    assert output.err == (
        "Error [crtsh] [invalid.example]: Source unavailable.\n"
    )
