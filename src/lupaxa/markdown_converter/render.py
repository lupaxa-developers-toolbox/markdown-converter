"""Render a document tree to CommonMark, GitHub, or Obsidian Markdown."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from lupaxa.markdown_converter.model import (
    Autolink,
    Block,
    CodeBlock,
    CodeSpan,
    Document,
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

_IMAGE_SUFFIXES = frozenset({"png", "jpg", "jpeg", "gif", "webp", "svg", "bmp", "avif"})
_TEXT_ESCAPES = frozenset("\\`*_[]")
_HTML_TEXT_ESCAPES = frozenset("<&")
_MARKDOWN_ESCAPES = _TEXT_ESCAPES | _HTML_TEXT_ESCAPES
_LINE_START_ESCAPES = frozenset("#-+>=|")
_ASCII_DIGITS = frozenset("0123456789")


def render(document: Document, flavour: str) -> str:
    """Join top-level blocks and prefix raw frontmatter when it is set."""
    parts = [_render_block(block, flavour) for block in document.blocks]
    if parts:
        body = "\n\n".join(parts)
        if not body.endswith("\n"):
            body += "\n"
    else:
        body = ""

    frontmatter = document.frontmatter
    if frontmatter is None:
        return body if body else "\n"
    if not frontmatter.endswith("\n"):
        frontmatter += "\n"
    if body:
        return frontmatter + "\n" + body
    return frontmatter


def _render_block(block: Block, flavour: str, *, at_line_start: bool = True) -> str:
    if isinstance(block, Heading):
        # The heading marker already occupies the start of the line.
        rendered = _render_inlines(block.inlines, flavour, at_line_start=False)
        return f"{'#' * block.level} {rendered}"
    if isinstance(block, Paragraph):
        return _render_inlines(block.inlines, flavour, at_line_start=at_line_start)
    if isinstance(block, CodeBlock):
        return _render_code_block(block)
    if isinstance(block, ThematicBreak):
        return "---"
    if isinstance(block, HtmlBlock):
        text = block.text
        if text.endswith("\n"):
            return text[:-1]
        return text
    if isinstance(block, Quote):
        return _render_quote(block, flavour)
    if isinstance(block, ListBlock):
        return _render_list(block, flavour)
    if isinstance(block, Table):
        if flavour == "commonmark":
            return _render_html_table(block, flavour)
        return _render_pipe_table(block, flavour)
    raise TypeError(f"unsupported block: {type(block).__name__}")


def _render_code_block(block: CodeBlock) -> str:
    text = block.text if block.text.endswith("\n") else f"{block.text}\n"
    return f"```{block.info}\n{text}```"


def _render_quote(block: Quote, flavour: str) -> str:
    inner = "\n\n".join(_render_block(child, flavour) for child in block.blocks)
    if block.kind == "callout":
        header = _callout_header(block, flavour)
        content = f"{header}\n\n{inner}" if inner else header
    else:
        content = inner
    return _prefix_quote(content)


def _callout_header(block: Quote, flavour: str) -> str:
    callout_type = block.callout_type or ""
    title = block.callout_title
    if flavour == "obsidian":
        if title:
            return f"[!{callout_type}] {title}"
        return f"[!{callout_type}]"
    label = f"{callout_type[:1].upper()}{callout_type[1:]}" if callout_type else ""
    if title:
        return f"**{label}:** {title}"
    return f"**{label}**"


def _prefix_quote(content: str) -> str:
    if content == "":
        return ">"
    lines = [">" if line == "" else f"> {line}" for line in content.split("\n")]
    return "\n".join(lines)


def _render_list(block: ListBlock, flavour: str) -> str:
    separator = "\n" if block.tight else "\n\n"
    items = [
        _render_list_item(item, flavour, block.ordered, block.start + index, block.tight)
        for index, item in enumerate(block.items)
    ]
    return separator.join(items)


def _render_list_item(
    item: ListItem,
    flavour: str,
    ordered: bool,
    number: int,
    tight: bool,
) -> str:
    if ordered:
        marker = f"{number}. "
        indent = len(marker)
    else:
        marker = "- "
        indent = 2
    if item.checked is not None and flavour != "commonmark":
        marker += "[x] " if item.checked else "[ ] "
    pieces = _item_pieces(item, flavour)
    body = ("\n" if tight else "\n\n").join(pieces)
    if body == "":
        return marker.rstrip(" ")
    lines = body.split("\n")
    continued = [_indent_continuation(line, indent) for line in lines[1:]]
    return "\n".join([f"{marker}{lines[0]}", *continued])


def _indent_continuation(line: str, indent: int) -> str:
    if line == "":
        return ""
    return f"{' ' * indent}{line}"


def _item_pieces(item: ListItem, flavour: str) -> list[str]:
    pieces: list[str] = []
    checkbox_pending = flavour == "commonmark" and item.checked is not None
    checkbox = "[x] " if item.checked else "[ ] "
    for index, child in enumerate(item.blocks):
        # A checkbox sits between the marker and the first block.
        at_line_start = index > 0 or item.checked is None
        text = _render_block(child, flavour, at_line_start=at_line_start)
        if checkbox_pending and isinstance(child, Paragraph):
            text = checkbox + text
            checkbox_pending = False
        pieces.append(text)
    return pieces


def _render_html_table(block: Table, flavour: str) -> str:
    header = "\n".join(
        f"<th>{_escape_html(_render_cell_html(cell, flavour))}</th>" for cell in block.header
    )
    rows = []
    for row in block.rows:
        cells = "\n".join(
            f"<td>{_escape_html(_render_cell_html(cell, flavour))}</td>" for cell in row
        )
        rows.append(f"<tr>\n{cells}\n</tr>")
    body = "\n".join(rows)
    return f"<table>\n<thead>\n<tr>\n{header}\n</tr>\n</thead>\n<tbody>\n{body}\n</tbody>\n</table>"


def _render_pipe_table(block: Table, flavour: str) -> str:
    alignments = [
        block.alignments[index] if index < len(block.alignments) else "none"
        for index in range(len(block.header))
    ]
    separator = "| " + " | ".join(_alignment_marker(align) for align in alignments) + " |"
    lines = [_pipe_row(block.header, flavour), separator]
    lines.extend(_pipe_row(row, flavour) for row in block.rows)
    return "\n".join(lines)


def _pipe_row(cells: list[list[Inline]], flavour: str) -> str:
    rendered = []
    for cell in cells:
        text = _render_inlines(cell, flavour, at_line_start=False)
        text = text.replace("\n", " ").replace("|", "\\|")
        rendered.append(text)
    return "| " + " | ".join(rendered) + " |"


def _alignment_marker(align: str) -> str:
    if align == "left":
        return ":---"
    if align == "center":
        return ":---:"
    if align == "right":
        return "---:"
    return "---"


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _render_cell_html(cell: list[Inline], flavour: str) -> str:
    """Render a cell for an HTML table without markdown escapes of ``<`` and ``&``."""
    return _render_inlines(cell, flavour, at_line_start=False, escape_html_chars=False)


def _render_inlines(
    inlines: list[Inline],
    flavour: str,
    *,
    at_line_start: bool,
    escape_html_chars: bool = True,
) -> str:
    parts: list[str] = []
    line_start = at_line_start
    for node in inlines:
        part = _render_inline(
            node,
            flavour,
            at_line_start=line_start,
            escape_html_chars=escape_html_chars,
        )
        parts.append(part)
        if part.endswith("\n"):
            line_start = True
        elif part:
            line_start = False
    return "".join(parts)


def _render_inline(
    node: Inline,
    flavour: str,
    *,
    at_line_start: bool,
    escape_html_chars: bool = True,
) -> str:
    if isinstance(node, Text):
        return _escape_text(
            node.text,
            at_line_start=at_line_start,
            escape_html_chars=escape_html_chars,
        )
    if isinstance(node, SoftBreak):
        return " "
    if isinstance(node, HardBreak):
        return "  \n"
    if isinstance(node, Em):
        inner = _wrapped_inlines(node.inlines, flavour, escape_html_chars)
        return f"*{inner}*"
    if isinstance(node, Strong):
        inner = _wrapped_inlines(node.inlines, flavour, escape_html_chars)
        return f"**{inner}**"
    if isinstance(node, CodeSpan):
        return _render_code_span(node.text)
    if isinstance(node, Link):
        return _render_link(node, flavour, escape_html_chars=escape_html_chars)
    if isinstance(node, Image):
        alt = _escape_text(node.alt, escape_html_chars=escape_html_chars)
        return f"![{alt}]({node.destination})"
    if isinstance(node, HtmlInline):
        return node.text
    if isinstance(node, Strike):
        inner = _wrapped_inlines(node.inlines, flavour, escape_html_chars)
        if flavour == "commonmark":
            return f"<del>{inner}</del>"
        return f"~~{inner}~~"
    if isinstance(node, Highlight):
        inner = _wrapped_inlines(node.inlines, flavour, escape_html_chars)
        if flavour == "obsidian":
            return f"=={inner}=="
        return f"<mark>{inner}</mark>"
    if isinstance(node, Autolink):
        if node.bare and flavour != "commonmark":
            return node.destination
        return f"<{node.destination}>"
    if isinstance(node, Wikilink):
        return _render_wikilink(node, flavour, escape_html_chars=escape_html_chars)
    if isinstance(node, Embed):
        return _render_embed(node, flavour, escape_html_chars=escape_html_chars)
    raise TypeError(f"unsupported inline: {type(node).__name__}")


def _wrapped_inlines(inlines: list[Inline], flavour: str, escape_html_chars: bool) -> str:
    """Render inlines that sit after a marker this writer just emitted."""
    return _render_inlines(
        inlines,
        flavour,
        at_line_start=False,
        escape_html_chars=escape_html_chars,
    )


def _escape_text(
    text: str,
    *,
    at_line_start: bool = False,
    escape_html_chars: bool = True,
) -> str:
    always = _MARKDOWN_ESCAPES if escape_html_chars else _TEXT_ESCAPES
    result: list[str] = []
    line_start = at_line_start
    index = 0
    while index < len(text):
        char = text[index]
        if char == "\n":
            result.append(char)
            line_start = True
            index += 1
            continue
        marker_end = _ordered_marker_delimiter(text, index) if line_start else None
        if marker_end is not None:
            # Digits are not CommonMark escapes. Escape the "." or ")" so the
            # number stays literal text and the line does not become a list.
            result.append(text[index:marker_end])
            result.append("\\")
            result.append(text[marker_end])
            index = marker_end + 1
            line_start = False
            continue
        if char in always or (line_start and char in _LINE_START_ESCAPES):
            result.append("\\")
        result.append(char)
        line_start = False
        index += 1
    return "".join(result)


def _ordered_marker_delimiter(text: str, index: int) -> int | None:
    """Index of ``.`` or ``)`` when ``text[index:]`` opens an ordered marker."""
    if index >= len(text) or text[index] not in _ASCII_DIGITS:
        return None
    end = index + 1
    while end < len(text) and text[end] in _ASCII_DIGITS:
        end += 1
    if end < len(text) and text[end] in ".)":
        return end
    return None


def _render_code_span(text: str) -> str:
    longest = 0
    run = 0
    for char in text:
        if char == "`":
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    fence = "`" * (longest + 1)
    if _code_span_needs_padding(text):
        return f"{fence} {text} {fence}"
    return f"{fence}{text}{fence}"


def _code_span_needs_padding(text: str) -> bool:
    if text.startswith("`") or text.endswith("`"):
        return True
    if text.startswith(" ") or text.endswith(" "):
        # A span of only spaces is left unchanged; padding would be kept.
        return text.strip(" ") != ""
    return False


def _render_link(node: Link, flavour: str, *, escape_html_chars: bool) -> str:
    inner = _wrapped_inlines(node.inlines, flavour, escape_html_chars)
    if node.title is None:
        return f"[{inner}]({node.destination})"
    title = node.title.replace('"', '\\"')
    return f'[{inner}]({node.destination} "{title}")'


def _render_wikilink(node: Wikilink, flavour: str, *, escape_html_chars: bool) -> str:
    if flavour == "obsidian":
        return _native_embed(node.target, node.heading, node.label, embed=False)
    label = _escape_text(
        _fallback_label(node.target, node.label),
        escape_html_chars=escape_html_chars,
    )
    destination = _fallback_destination(node.target, node.heading, image=False)
    return f"[{label}]({destination})"


def _render_embed(node: Embed, flavour: str, *, escape_html_chars: bool) -> str:
    image = _is_image_target(node.target)
    if flavour == "obsidian":
        return _native_embed(node.target, node.heading, node.label, embed=True)
    if image:
        alt = _escape_text(
            _image_alt(node.target, node.label),
            escape_html_chars=escape_html_chars,
        )
        destination = _fallback_destination(node.target, node.heading, image=True)
        return f"![{alt}]({destination})"
    label = _escape_text(
        _fallback_label(node.target, node.label),
        escape_html_chars=escape_html_chars,
    )
    destination = _fallback_destination(node.target, node.heading, image=False)
    return f"[{label}]({destination})"


def _native_embed(target: str, heading: str | None, label: str | None, *, embed: bool) -> str:
    body = target
    if heading:
        body = f"{body}#{heading}"
    if label:
        body = f"{body}|{label}"
    prefix = "!" if embed else ""
    return f"{prefix}[[{body}]]"


def _is_image_target(target: str) -> bool:
    suffix = Path(target).suffix.lower().removeprefix(".")
    return suffix in _IMAGE_SUFFIXES


def _fallback_destination(target: str, heading: str | None, *, image: bool) -> str:
    encoded = "/".join(quote(part, safe="") for part in target.split("/"))
    if not image and not target.endswith(".md"):
        encoded += ".md"
    if heading is not None:
        encoded += f"#{_slug_heading(heading)}"
    return encoded


def _slug_heading(heading: str) -> str:
    if heading.startswith("^"):
        return heading
    slug: list[str] = []
    for char in heading.lower():
        if char == " ":
            slug.append("-")
        elif char.isalnum() or char == "-":
            slug.append(char)
    return "".join(slug)


def _fallback_label(target: str, label: str | None) -> str:
    if label is not None:
        return label
    return target.rsplit("/", 1)[-1].removesuffix(".md")


def _image_alt(target: str, label: str | None) -> str:
    if label is None or label.isdigit():
        return Path(target).stem
    return label
