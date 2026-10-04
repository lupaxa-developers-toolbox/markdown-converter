"""Parse flavour syntax into the document tree."""

from __future__ import annotations

import pytest

from lupaxa.markdown_converter import MarkdownConverter, MarkdownConverterError
from lupaxa.markdown_converter.model import (
    CodeSpan,
    Heading,
    ListBlock,
    ListItem,
    Paragraph,
    Quote,
    Text,
    Wikilink,
)
from lupaxa.markdown_converter.parse import parse_body


def test_atx_heading() -> None:
    blocks = parse_body("# Title\n", "commonmark")
    assert isinstance(blocks[0], Heading)
    assert blocks[0].level == 1


def test_setext_heading_becomes_a_heading_node() -> None:
    blocks = parse_body("Title\n=====\n", "commonmark")
    assert isinstance(blocks[0], Heading)
    assert blocks[0].level == 1


def test_commonmark_checkbox_text_is_not_a_task() -> None:
    blocks = parse_body("- [ ] todo\n", "commonmark")
    item = blocks[0].items[0]
    assert isinstance(item, ListItem)
    assert item.checked is None


def test_github_checkbox_is_a_task() -> None:
    blocks = parse_body("- [X] done\n", "github")
    assert blocks[0].items[0].checked is True


def test_wikilink_inside_a_paragraph() -> None:
    blocks = parse_body("See [[Page|Alias]].\n", "obsidian")
    assert isinstance(blocks[0], Paragraph)
    assert isinstance(blocks[0].inlines[1], Wikilink)
    assert blocks[0].inlines[1].label == "Alias"


def test_wikilink_in_a_fence_stays_text() -> None:
    blocks = parse_body("```\n[[Page]]\n```\n", "obsidian")
    assert "[[Page]]" in blocks[0].text


def test_html_entity_in_paragraph_decodes_ampersand() -> None:
    blocks = parse_body("AT&amp;T\n", "commonmark")
    assert isinstance(blocks[0], Paragraph)
    inline = blocks[0].inlines[0]
    assert isinstance(inline, Text)
    assert "AT&T" in inline.text
    assert inline.text != "ATT"


def test_callout_drops_the_fold_marker() -> None:
    blocks = parse_body("> [!note]- Title\n> body\n", "obsidian")
    assert isinstance(blocks[0], Quote)
    assert blocks[0].kind == "callout"
    assert blocks[0].callout_type == "note"
    assert blocks[0].callout_title == "Title"


def test_obsidian_wikilink_to_github() -> None:
    text = MarkdownConverter("[[folder/My Page#Hello World]]\n", flavour="obsidian").to_github()
    assert text == "[My Page](folder/My%20Page.md#hello-world)\n"


def test_github_table_survives_obsidian_and_falls_back_for_commonmark() -> None:
    source = "| A | B |\n| --- | ---: |\n| 1 | 2 |\n"
    assert (
        MarkdownConverter(source, flavour="github").to_obsidian()
        == "| A | B |\n| --- | ---: |\n| 1 | 2 |\n"
    )
    common = MarkdownConverter(source, flavour="github").to_commonmark()
    assert common.startswith("<table>\n")
    assert "| A |" not in common


def test_html_table_is_not_promoted() -> None:
    source = "<table><tr><td>A</td></tr></table>\n"
    assert "<table>" in MarkdownConverter(source, flavour="commonmark").to_github()
    assert "| A |" not in MarkdownConverter(source, flavour="commonmark").to_github()


def test_checkbox_text_is_not_promoted() -> None:
    source = "- [ ] todo\n"
    assert MarkdownConverter(source, flavour="commonmark").to_github() == "- \\[ \\] todo\n"


def test_fence_hides_a_wikilink() -> None:
    source = "```\n[[Page]]\n```\n"
    assert "[[Page]]" in MarkdownConverter(source, flavour="obsidian").to_github()


def test_frontmatter_round_trip_with_empty_body() -> None:
    source = "---\ntitle: Note\n---\n"
    assert MarkdownConverter(source, flavour="OBSIDIAN").to_commonmark() == source


def test_same_flavour_is_canonical() -> None:
    assert MarkdownConverter("Title\n=====\n", flavour="commonmark").to_commonmark() == "# Title\n"


def test_unknown_flavour_and_non_string() -> None:
    with pytest.raises(MarkdownConverterError):
        MarkdownConverter("hi", flavour="rst")
    with pytest.raises(MarkdownConverterError):
        MarkdownConverter(b"hi")  # type: ignore[arg-type]


def test_strike_and_bare_url_fall_back() -> None:
    source = "~~old~~ and https://example.com\n"
    assert (
        MarkdownConverter(source, flavour="github").to_commonmark()
        == "<del>old</del> and <https://example.com>\n"
    )
    assert (
        MarkdownConverter(source, flavour="github").to_obsidian()
        == "~~old~~ and https://example.com\n"
    )


def test_highlight_and_callout_fall_back() -> None:
    source = "==hi==\n\n> [!tip] Look\n> here\n"
    github = MarkdownConverter(source, flavour="obsidian").to_github()
    assert "<mark>hi</mark>" in github
    assert "**Tip:** Look" in github
    assert "[!tip]" not in github
    kept = MarkdownConverter(source, flavour="obsidian").to_obsidian()
    assert "==hi==" in kept
    assert "[!tip] Look" in kept


def test_image_embed_and_resize_hint() -> None:
    source = "![[shot.png|100]]\n"
    assert MarkdownConverter(source, flavour="obsidian").to_github() == "![shot](shot.png)\n"
    assert MarkdownConverter(source, flavour="obsidian").to_obsidian() == "![[shot.png|100]]\n"


def test_indented_code_becomes_a_fence() -> None:
    source = "    code\n"
    assert MarkdownConverter(source, flavour="commonmark").to_commonmark() == "```\ncode\n```\n"


def test_ordered_list_keeps_its_start() -> None:
    source = "3. third\n"
    assert MarkdownConverter(source, flavour="commonmark").to_commonmark() == "3. third\n"


def test_hard_break_and_quote_and_image() -> None:
    source = "A hard  \nbreak.\n\n> quoted\n\n![alt](shot.png)\n"
    text = MarkdownConverter(source, flavour="commonmark").to_commonmark()
    assert "A hard  \nbreak." in text
    assert "> quoted" in text
    assert "![alt](shot.png)" in text


def test_reference_link_is_written_inline() -> None:
    source = "See [ref].\n\n[ref]: https://example.com/ref\n"
    assert (
        MarkdownConverter(source, flavour="commonmark").to_commonmark()
        == "See [ref](https://example.com/ref).\n"
    )


def test_raw_html_is_preserved() -> None:
    source = "<div>raw</div>\n"
    assert MarkdownConverter(source, flavour="commonmark").to_github() == "<div>raw</div>\n"


def _render_same(source: str, flavour: str) -> str:
    converter = MarkdownConverter(source, flavour=flavour)
    if flavour == "github":
        return converter.to_github()
    if flavour == "obsidian":
        return converter.to_obsidian()
    return converter.to_commonmark()


def _assert_round_trip(source: str, flavour: str = "commonmark") -> str:
    first = _render_same(source, flavour)
    second = _render_same(first, flavour)
    assert second == first
    return first


def test_bullet_list_with_a_nested_list_round_trips() -> None:
    first = _assert_round_trip("- parent\n  - child\n")
    blocks = parse_body(first, "commonmark")
    assert len(blocks) == 1
    assert isinstance(blocks[0], ListBlock)
    assert not blocks[0].ordered
    assert any(isinstance(child, ListBlock) for child in blocks[0].items[0].blocks)


def test_ordered_list_with_a_nested_list_round_trips() -> None:
    first = _assert_round_trip("1. parent\n   - child\n")
    blocks = parse_body(first, "commonmark")
    assert len(blocks) == 1
    assert isinstance(blocks[0], ListBlock)
    assert blocks[0].ordered
    nested = [child for child in blocks[0].items[0].blocks if isinstance(child, ListBlock)]
    assert len(nested) == 1


def test_ordered_list_second_paragraph_round_trips() -> None:
    first = _assert_round_trip("1. first\n\n   second\n")
    blocks = parse_body(first, "commonmark")
    assert len(blocks) == 1
    assert isinstance(blocks[0], ListBlock)
    assert len(blocks[0].items[0].blocks) == 2
    blank = [line for line in first.split("\n") if line and not line.strip()]
    assert blank == []


def test_task_item_continuation_round_trips() -> None:
    first = _assert_round_trip("- [ ] todo  \n  continued\n", "github")
    blocks = parse_body(first, "github")
    assert len(blocks) == 1
    assert isinstance(blocks[0], ListBlock)
    assert blocks[0].items[0].checked is False
    assert "continued" in first


def test_code_span_with_a_backtick_round_trips() -> None:
    first = _assert_round_trip("`` ` ``\n")
    blocks = parse_body(first, "commonmark")
    assert isinstance(blocks[0], Paragraph)
    spans = [inline for inline in blocks[0].inlines if isinstance(inline, CodeSpan)]
    assert len(spans) == 1
    assert spans[0].text == "`"
    assert _render_same("`code`\n", "commonmark") == "`code`\n"


def test_escaped_markers_stay_paragraphs() -> None:
    cases = (
        ("\\- not a list\n", "- not a list"),
        ("\\# not a heading\n", "# not a heading"),
    )
    for source, plain in cases:
        text = _render_same(source, "commonmark")
        assert not text.startswith(("-", "+", ">", "#"))
        blocks = parse_body(text, "commonmark")
        assert len(blocks) == 1
        assert isinstance(blocks[0], Paragraph)
        rendered = "".join(inline.text for inline in blocks[0].inlines if isinstance(inline, Text))
        assert rendered == plain
