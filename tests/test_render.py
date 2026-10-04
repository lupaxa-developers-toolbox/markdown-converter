"""Renderer coverage starts with a constructable document tree."""

from __future__ import annotations

from lupaxa.markdown_converter.model import (
    Autolink,
    CodeBlock,
    Document,
    Em,
    Embed,
    Heading,
    Highlight,
    Link,
    ListBlock,
    ListItem,
    Paragraph,
    Quote,
    Strike,
    Strong,
    Table,
    Text,
    ThematicBreak,
    Wikilink,
)
from lupaxa.markdown_converter.render import render


def test_document_holds_blocks() -> None:
    document = Document(frontmatter=None, blocks=[Heading(1, [Text("Title")])])
    assert document.blocks[0].level == 1
    assert isinstance(document.blocks[0], Heading)
    paragraph = Paragraph([Text("Hi")])
    assert paragraph.inlines[0].text == "Hi"


def _doc(*blocks: object) -> Document:
    return Document(None, list(blocks))  # type: ignore[arg-type]


def test_commonmark_heading_paragraph_and_break() -> None:
    document = _doc(Heading(2, [Text("Section")]), Paragraph([Text("Hello")]), ThematicBreak())
    assert render(document, "commonmark") == "## Section\n\nHello\n\n---\n"


def test_emphasis_and_code_fence() -> None:
    document = _doc(
        Paragraph([Text("say "), Em([Text("hi")]), Text(" and "), Strong([Text("go")])]),
        CodeBlock("py", "print(1)\n"),
    )
    assert render(document, "commonmark") == "say *hi* and **go**\n\n```py\nprint(1)\n```\n"


def test_tight_nested_list() -> None:
    child = ListBlock(False, 1, True, [ListItem(None, [Paragraph([Text("child")])])])
    parent = ListBlock(False, 1, True, [ListItem(None, [Paragraph([Text("parent")]), child])])
    assert render(_doc(parent), "commonmark") == "- parent\n  - child\n"


def test_task_and_table_fall_back_for_commonmark() -> None:
    items = ListBlock(False, 1, True, [ListItem(True, [Paragraph([Text("done")])])])
    table = Table([[Text("A")], [Text("B")]], ["none", "right"], [[[Text("1")], [Text("2")]]])
    assert render(_doc(items), "commonmark") == "- [x] done\n"
    html = render(_doc(table), "commonmark")
    assert html.startswith("<table>\n<thead>\n<tr>\n")
    assert "<td>2</td>" in html
    assert "text-align" not in html


def test_github_keeps_task_strike_and_table() -> None:
    items = ListBlock(False, 1, True, [ListItem(False, [Paragraph([Text("todo")])])])
    strike = Paragraph([Strike([Text("old")])])
    table = Table([[Text("A")]], ["left"], [[[Text("1")]]])
    assert render(_doc(items), "github") == "- [ ] todo\n"
    assert render(_doc(strike), "github") == "~~old~~\n"
    assert render(_doc(table), "github") == "| A |\n| :--- |\n| 1 |\n"


def test_obsidian_nodes_fall_back_outside_obsidian() -> None:
    wiki = Paragraph([Wikilink("folder/My Page", "Hello World", None)])
    image = Paragraph([Embed("shot.png", None, "100")])
    note = Paragraph([Embed("Note", None, None)])
    mark = Paragraph([Highlight([Text("hi")])])
    callout = Quote("callout", "warning", "Title", [Paragraph([Text("body")])])
    assert render(_doc(wiki), "github") == "[My Page](folder/My%20Page.md#hello-world)\n"
    assert render(_doc(image), "github") == "![shot](shot.png)\n"
    assert render(_doc(note), "github") == "[Note](Note.md)\n"
    assert render(_doc(mark), "github") == "<mark>hi</mark>\n"
    assert render(_doc(callout), "commonmark") == "> **Warning:** Title\n>\n> body\n"


def test_obsidian_keeps_native_syntax() -> None:
    wiki = Paragraph([Wikilink("Page", None, "Alias")])
    assert render(_doc(wiki), "obsidian") == "[[Page|Alias]]\n"


def test_bare_autolink_becomes_angle_brackets_in_commonmark() -> None:
    node = Paragraph([Autolink("https://example.com", True)])
    assert render(_doc(node), "commonmark") == "<https://example.com>\n"
    assert render(_doc(node), "github") == "https://example.com\n"


def test_ordinary_link_stays_a_link() -> None:
    node = Paragraph([Link("Page.md", None, [Text("Page")])])
    assert render(_doc(node), "github") == "[Page](Page.md)\n"
    assert render(_doc(node), "obsidian") == "[Page](Page.md)\n"


def test_frontmatter_is_prefixed_unchanged() -> None:
    document = Document("---\ntitle: Note\n---\n", [Heading(1, [Text("Title")])])
    assert render(document, "commonmark") == "---\ntitle: Note\n---\n\n# Title\n"


def test_empty_body_with_frontmatter() -> None:
    document = Document("---\ntitle: Note\n---\n", [])
    assert render(document, "github") == "---\ntitle: Note\n---\n"
