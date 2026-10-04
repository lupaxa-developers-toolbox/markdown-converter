"""Convert a document between CommonMark, GitHub, and Obsidian."""

from __future__ import annotations

from lupaxa.markdown_converter.errors import MarkdownConverterError
from lupaxa.markdown_converter.frontmatter import split_frontmatter
from lupaxa.markdown_converter.model import Document
from lupaxa.markdown_converter.parse import parse_body
from lupaxa.markdown_converter.render import render

_FLAVOURS = frozenset({"commonmark", "github", "obsidian"})


def normalize_flavour(flavour: str) -> str:
    """Return ``flavour`` stripped and lower-cased when it is a known name."""
    normalised = flavour.strip().lower()
    if normalised not in _FLAVOURS:
        raise MarkdownConverterError(f"unknown flavour: {flavour}")
    return normalised


class MarkdownConverter:
    """A Markdown document parsed in one flavour and rendered in another."""

    def __init__(self, data: str, flavour: str = "commonmark") -> None:
        if not isinstance(data, str):
            raise MarkdownConverterError("document must be a string")
        self.flavour = normalize_flavour(flavour)
        frontmatter, body = split_frontmatter(data)
        body = body.replace("\r\n", "\n").replace("\r", "\n")
        try:
            blocks = parse_body(body, self.flavour)
        except Exception as exc:
            raise MarkdownConverterError("document could not be parsed") from exc
        self._document = Document(frontmatter, blocks)

    def to_commonmark(self) -> str:
        """Render the document as CommonMark."""
        return render(self._document, "commonmark")

    def to_github(self) -> str:
        """Render the document as GitHub Flavored Markdown."""
        return render(self._document, "github")

    def to_obsidian(self) -> str:
        """Render the document as Obsidian Markdown."""
        return render(self._document, "obsidian")
