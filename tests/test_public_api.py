"""Public package surface."""

from __future__ import annotations

import pathlib

import lupaxa.markdown_converter as markdown_converter

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_namespace_package_has_no_init() -> None:
    assert not (REPO_ROOT / "src" / "lupaxa" / "__init__.py").is_file()


def test_public_all_lists_documented_names() -> None:
    assert set(markdown_converter.__all__) >= {
        "MarkdownConverter",
        "MarkdownConverterError",
        "__version__",
        "get_version",
    }
