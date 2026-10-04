"""Argument parsing and exit codes for the markdown converter."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import NoReturn

from lupaxa.markdown_converter import MarkdownConverter, MarkdownConverterError
from lupaxa.markdown_converter.converter import normalize_flavour
from lupaxa.markdown_converter.version import get_version

_RENDER = {
    "commonmark": MarkdownConverter.to_commonmark,
    "github": MarkdownConverter.to_github,
    "obsidian": MarkdownConverter.to_obsidian,
}


class _Parser(argparse.ArgumentParser):
    """Parser that reports usage mistakes as one ``Error:`` line."""

    def error(self, message: str) -> NoReturn:
        self.exit(2, f"Error: {message}\n")


class _InputError(Exception):
    """Input or output the command line cannot use."""


def _build_parser() -> _Parser:
    parser = _Parser(
        prog="markdown-converter",
        description="Convert a Markdown document between CommonMark, GitHub, and Obsidian.",
    )
    parser.add_argument(
        "--from",
        required=True,
        dest="source",
        metavar="FLAVOUR",
        help="source flavour: commonmark, github, or obsidian",
    )
    parser.add_argument(
        "--to",
        required=True,
        dest="target",
        metavar="FLAVOUR",
        help="target flavour: commonmark, github, or obsidian",
    )
    parser.add_argument(
        "file",
        nargs="?",
        metavar="FILE",
        help="input path; omit or pass - to read stdin",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="PATH",
        help="output path; omit to write stdout",
    )
    parser.add_argument("--version", action="version", version=get_version())
    return parser


def _read_input(path: str | None) -> str:
    if path is None or path == "-":
        return sys.stdin.read()
    source = Path(path)
    if not source.exists():
        raise _InputError(f"no such file: {path}")
    if source.is_dir():
        raise _InputError(f"{path} is a directory")
    try:
        return source.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise _InputError(f"{path} is not valid UTF-8") from exc
    except OSError as exc:
        raise _InputError(str(exc)) from exc


def _convert(data: str, source: str, target: str) -> str:
    converter = MarkdownConverter(data, flavour=source)
    flavour = normalize_flavour(target)
    render = _RENDER.get(flavour)
    if render is None:
        raise MarkdownConverterError(f"unknown flavour: {target}")
    return render(converter)


def _write_output(path: str | None, text: str) -> None:
    if path is None:
        sys.stdout.write(text)
        return
    try:
        Path(path).write_text(text, encoding="utf-8")
    except OSError as exc:
        raise _InputError(str(exc)) from exc


def main(argv: list[str] | None = None) -> int:
    """Convert one document. Return 0 on success and 2 on an input or convert error."""
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # argparse exits 0 for --help and --version. error() still exits 2.
        if exc.code in (0, None):
            return 0
        raise

    try:
        text = _convert(_read_input(args.file), args.source, args.target)
        _write_output(args.output, text)
    except (MarkdownConverterError, _InputError) as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 2
    return 0
