"""CLI exit codes and streams."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from lupaxa.markdown_converter.cli import main
from lupaxa.markdown_converter.version import get_version


def test_stdin_writes_stdout(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("# Title\n"))
    code = main(["--from", "commonmark", "--to", "commonmark", "-"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out == "# Title\n"
    assert captured.err == ""


def test_file_round_trip(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "note.md"
    source.write_text("# Title\n", encoding="utf-8")
    code = main(["--from", "commonmark", "--to", "commonmark", str(source)])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out == "# Title\n"
    assert captured.err == ""


def test_output_file(tmp_path: Path) -> None:
    source = tmp_path / "note.md"
    dest = tmp_path / "out.md"
    source.write_text("[[Page]]\n", encoding="utf-8")
    code = main(["--from", "obsidian", "--to", "github", str(source), "-o", str(dest)])
    assert code == 0
    assert dest.read_text(encoding="utf-8") == "[Page](Page.md)\n"


def test_missing_file_exits_2(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    code = main(["--from", "commonmark", "--to", "github", str(tmp_path / "missing.md")])
    assert code == 2
    assert capsys.readouterr().err.startswith("Error:")


def test_directory_exits_2(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    code = main(["--from", "commonmark", "--to", "github", str(tmp_path)])
    assert code == 2
    assert capsys.readouterr().err.startswith("Error:")


def test_help_and_version(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--help"]) == 0
    assert "markdown-converter" in capsys.readouterr().out
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == get_version()
