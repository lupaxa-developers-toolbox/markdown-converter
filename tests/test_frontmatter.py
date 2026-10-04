"""Leading YAML frontmatter is copied, not parsed."""

from __future__ import annotations

from lupaxa.markdown_converter.frontmatter import split_frontmatter


def test_no_fence_returns_the_whole_text() -> None:
    assert split_frontmatter("# Title\n") == (None, "# Title\n")


def test_fence_is_byte_for_byte() -> None:
    text = "---\r\ntitle: Note\r\n---\r\n# Title\n"
    front, body = split_frontmatter(text)
    assert front == "---\r\ntitle: Note\r\n---\r\n"
    assert body == "# Title\n"


def test_unclosed_fence_is_body() -> None:
    text = "---\ntitle: Note\n# Title\n"
    assert split_frontmatter(text) == (None, text)


def test_later_rule_is_not_frontmatter() -> None:
    text = "# Title\n\n---\n"
    assert split_frontmatter(text) == (None, text)
