"""Tests for the Semillero command-line interface."""

import sys

import pytest

from semillero import cli
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
