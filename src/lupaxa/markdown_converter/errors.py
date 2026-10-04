"""Errors raised by the markdown converter."""

from __future__ import annotations


class MarkdownConverterError(Exception):
    """A caller mistake or a document that cannot be parsed."""
