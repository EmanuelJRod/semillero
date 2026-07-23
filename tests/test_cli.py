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
