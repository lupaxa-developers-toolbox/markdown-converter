"""Parse flavour syntax into the document tree."""

from __future__ import annotations

import re

from markdown_it import MarkdownIt
from markdown_it.token import Token

from lupaxa.markdown_converter.model import (
    Align,
    Autolink,
    Block,
    CodeBlock,
    CodeSpan,
    Em,
    Embed,
    HardBreak,
    Heading,
    Highlight,
    HtmlBlock,
    HtmlInline,
    Image,
    Inline,
    Link,
    ListBlock,
    ListItem,
    Paragraph,
    Quote,
    SoftBreak,
    Strike,
    Strong,
    Table,
    Text,
    ThematicBreak,
    Wikilink,
)
from lupaxa.markdown_converter.obsidian import register_obsidian

# Closing ] is part of `[!type]`; the fold marker, when present, follows it.
_CALLOUT_RE = re.compile(r"^\[!([A-Za-z0-9_-]+)\][+-]?(?:[ \t]+(.*?))?[ \t]*$")
_URL_RE = re.compile(r"https?://[^\s<>]+")
_EMAIL_RE = re.compile(
    r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+"
)
_URL_TRAILING = ".,;:!?"
_TASK_PREFIXES: tuple[tuple[str, bool], ...] = (
    ("[ ] ", False),
    ("[x] ", True),
    ("[X] ", True),
)


def parse_body(body: str, flavour: str) -> list[Block]:
    """Parse a Markdown body into blocks for one flavour."""
    md = MarkdownIt("commonmark", {"linkify": False})
    if flavour in {"github", "obsidian"}:
        md.enable(["table", "strikethrough"])
    if flavour == "obsidian":
        register_obsidian(md)
    return _Parser(md.parse(body), flavour).blocks_until(None)


class _Parser:
    def __init__(self, tokens: list[Token], flavour: str) -> None:
        self.tokens = tokens
        self.flavour = flavour
        self.index = 0

    def blocks_until(self, close: str | None) -> list[Block]:
        blocks: list[Block] = []
        while self.index < len(self.tokens):
            if close is not None and self.tokens[self.index].type == close:
                break
            block = self._one_block()
            if block is not None:
                blocks.append(block)
        return blocks

    def _one_block(self) -> Block | None:
        token = self.tokens[self.index]
        kind = token.type
        if kind == "heading_open":
            return self._heading(token)
        if kind == "paragraph_open":
            return self._paragraph()
        if kind == "fence":
            self.index += 1
            return CodeBlock(token.info, token.content)
        if kind == "code_block":
            self.index += 1
            return CodeBlock("", token.content)
        if kind == "hr":
            self.index += 1
            return ThematicBreak()
        if kind == "html_block":
            self.index += 1
            return HtmlBlock(token.content)
        if kind == "blockquote_open":
            return self._quote()
        if kind in {"bullet_list_open", "ordered_list_open"}:
            return self._list(kind == "ordered_list_open")
        if kind == "table_open":
            return self._table()
        self.index += 1
        return None

    def _heading(self, token: Token) -> Heading:
        level = int(token.tag[1])
        self.index += 1
        inlines = self._take_inline()
        self._skip("heading_close")
        return Heading(level, inlines)

    def _paragraph(self) -> Paragraph:
        self.index += 1
        inlines = self._take_inline()
        self._skip("paragraph_close")
        return Paragraph(inlines)

    def _quote(self) -> Quote:
        self.index += 1
        blocks = self.blocks_until("blockquote_close")
        self._skip("blockquote_close")
        quote = Quote("quote", None, None, blocks)
        if self.flavour == "obsidian":
            _apply_callout(quote)
        return quote

    def _list(self, ordered: bool) -> ListBlock:
        close = "ordered_list_close" if ordered else "bullet_list_close"
        self.index += 1
        items: list[ListItem] = []
        start = 1
        captured_start = False
        while self.index < len(self.tokens) and self.tokens[self.index].type != close:
            if self.tokens[self.index].type != "list_item_open":
                self.index += 1
                continue
            if ordered and not captured_start:
                info = self.tokens[self.index].info
                if info.isdigit():
                    start = int(info)
                captured_start = True
            items.append(self._list_item())
        self._skip(close)
        tight = all(
            len(item.blocks) == 1 and isinstance(item.blocks[0], Paragraph) for item in items
        )
        return ListBlock(ordered, start, tight, items)

    def _list_item(self) -> ListItem:
        self.index += 1
        blocks = self.blocks_until("list_item_close")
        self._skip("list_item_close")
        checked: bool | None = None
        if self.flavour in {"github", "obsidian"} and blocks and isinstance(blocks[0], Paragraph):
            checked = _strip_checkbox(blocks[0])
        return ListItem(checked, blocks)

    def _table(self) -> Table:
        header: list[list[Inline]] = []
        alignments: list[Align] = []
        rows: list[list[list[Inline]]] = []
        in_body = False
        row: list[list[Inline]] | None = None
        self.index += 1
        while self.index < len(self.tokens) and self.tokens[self.index].type != "table_close":
            token = self.tokens[self.index]
            kind = token.type
            if kind == "tbody_open":
                in_body = True
                self.index += 1
            elif kind == "tbody_close":
                in_body = False
                self.index += 1
            elif kind == "tr_open" and in_body:
                row = []
                self.index += 1
            elif kind == "tr_close" and row is not None:
                rows.append(row)
                row = None
                self.index += 1
            elif kind == "th_open":
                alignments.append(_alignment(token.attrs.get("style")))
                self.index += 1
                header.append(self._take_inline())
                self._skip("th_close")
            elif kind == "td_open" and row is not None:
                self.index += 1
                row.append(self._take_inline())
                self._skip("td_close")
            else:
                self.index += 1
        self._skip("table_close")
        return Table(header, alignments, rows)

    def _take_inline(self) -> list[Inline]:
        if self.index < len(self.tokens) and self.tokens[self.index].type == "inline":
            children = self.tokens[self.index].children or []
            self.index += 1
            return _read_inlines(children, self.flavour, in_link=False)
        return []

    def _skip(self, kind: str) -> None:
        if self.index < len(self.tokens) and self.tokens[self.index].type == kind:
            self.index += 1


def _alignment(style: object) -> Align:
    if style == "text-align:left":
        return "left"
    if style == "text-align:center":
        return "center"
    if style == "text-align:right":
        return "right"
    return "none"


def _apply_callout(quote: Quote) -> None:
    if not quote.blocks or not isinstance(quote.blocks[0], Paragraph):
        return
    paragraph = quote.blocks[0]
    line: list[Inline] = []
    rest_at: int | None = None
    for index, inline in enumerate(paragraph.inlines):
        if isinstance(inline, (SoftBreak, HardBreak)):
            rest_at = index + 1
            break
        line.append(inline)
    if not line or not all(isinstance(inline, Text) for inline in line):
        return
    text = "".join(inline.text for inline in line if isinstance(inline, Text))
    match = _CALLOUT_RE.match(text)
    if match is None:
        return
    quote.kind = "callout"
    quote.callout_type = match.group(1)
    title = match.group(2)
    quote.callout_title = title if title else None
    if rest_at is None or rest_at >= len(paragraph.inlines):
        quote.blocks.pop(0)
        return
    paragraph.inlines = paragraph.inlines[rest_at:]
    if not paragraph.inlines:
        quote.blocks.pop(0)


def _strip_checkbox(paragraph: Paragraph) -> bool | None:
    if not paragraph.inlines or not isinstance(paragraph.inlines[0], Text):
        return None
    first = paragraph.inlines[0]
    for prefix, checked in _TASK_PREFIXES:
        if first.text.startswith(prefix):
            rest = first.text[len(prefix) :]
            if rest:
                first.text = rest
            else:
                paragraph.inlines.pop(0)
            return checked
    return None


def _read_inlines(tokens: list[Token], flavour: str, *, in_link: bool) -> list[Inline]:
    result: list[Inline] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        kind = token.type
        if kind in {"text", "text_special"}:
            if flavour in {"github", "obsidian"} and not in_link:
                result.extend(_split_bare(token.content))
            else:
                result.append(Text(token.content))
            index += 1
        elif kind == "em_open":
            inner, index = _until(tokens, index, "em_open", "em_close")
            result.append(Em(_read_inlines(inner, flavour, in_link=in_link)))
        elif kind == "strong_open":
            inner, index = _until(tokens, index, "strong_open", "strong_close")
            result.append(Strong(_read_inlines(inner, flavour, in_link=in_link)))
        elif kind == "s_open":
            inner, index = _until(tokens, index, "s_open", "s_close")
            result.append(Strike(_read_inlines(inner, flavour, in_link=in_link)))
        elif kind == "mark_open":
            inner, index = _until(tokens, index, "mark_open", "mark_close")
            result.append(Highlight(_read_inlines(inner, flavour, in_link=in_link)))
        elif kind == "code_inline":
            result.append(CodeSpan(token.content))
            index += 1
        elif kind == "softbreak":
            result.append(SoftBreak())
            index += 1
        elif kind == "hardbreak":
            result.append(HardBreak())
            index += 1
        elif kind == "html_inline":
            result.append(HtmlInline(token.content))
            index += 1
        elif kind == "image":
            result.append(Image(_attr_str(token, "src"), token.content))
            index += 1
        elif kind == "link_open":
            inner, index = _until(tokens, index, "link_open", "link_close")
            if token.markup == "autolink":
                result.append(Autolink(_joined_text(inner), bare=False))
            else:
                title = token.attrs.get("title")
                result.append(
                    Link(
                        _attr_str(token, "href"),
                        title if isinstance(title, str) else None,
                        _read_inlines(inner, flavour, in_link=True),
                    )
                )
        elif kind in {"wikilink", "embed"}:
            result.append(_wiki(token.content, embed=kind == "embed"))
            index += 1
        else:
            index += 1
    return result


def _until(
    tokens: list[Token], open_index: int, open_kind: str, close_kind: str
) -> tuple[list[Token], int]:
    depth = 1
    index = open_index + 1
    start = index
    while index < len(tokens):
        kind = tokens[index].type
        if kind == open_kind:
            depth += 1
        elif kind == close_kind:
            depth -= 1
            if depth == 0:
                return tokens[start:index], index + 1
        index += 1
    return tokens[start:], index


def _joined_text(tokens: list[Token]) -> str:
    return "".join(token.content for token in tokens if token.type == "text")


def _attr_str(token: Token, name: str) -> str:
    value = token.attrs.get(name, "")
    if isinstance(value, str):
        return value
    return str(value)


def _wiki(content: str, *, embed: bool) -> Wikilink | Embed:
    if "|" in content:
        body, label = content.split("|", 1)
    else:
        body = content
        label = None
    if "#" in body:
        target, heading = body.split("#", 1)
    else:
        target = body
        heading = None
    if embed:
        return Embed(target, heading, label)
    return Wikilink(target, heading, label)


def _split_bare(text: str) -> list[Inline]:
    pieces: list[Inline] = []
    pos = 0
    while pos < len(text):
        url_match = _URL_RE.search(text, pos)
        email_match = _EMAIL_RE.search(text, pos)
        url_first = url_match is not None and (
            email_match is None or url_match.start() <= email_match.start()
        )
        match = url_match if url_first else email_match
        if match is None:
            pieces.append(Text(text[pos:]))
            break
        is_url = url_first
        if match.start() > pos:
            pieces.append(Text(text[pos : match.start()]))
        raw = match.group(0)
        if is_url:
            destination = raw.rstrip(_URL_TRAILING)
            if destination:
                pieces.append(Autolink(destination, bare=True))
                pos = match.start() + len(destination)
                continue
        else:
            pieces.append(Autolink(raw, bare=True))
        pos = match.end()
    return pieces
