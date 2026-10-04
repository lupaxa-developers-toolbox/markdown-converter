"""Document tree shared by the markdown parsers and renderers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Flavour = Literal["commonmark", "github", "obsidian"]
Align = Literal["left", "center", "right", "none"]


@dataclass(slots=True)
class Heading:
    level: int
    inlines: list[Inline]


@dataclass(slots=True)
class Paragraph:
    inlines: list[Inline]


@dataclass(slots=True)
class CodeBlock:
    info: str
    text: str


@dataclass(slots=True)
class Quote:
    kind: Literal["quote", "callout"]
    callout_type: str | None
    callout_title: str | None
    blocks: list[Block]


@dataclass(slots=True)
class ListItem:
    checked: bool | None
    blocks: list[Block]


@dataclass(slots=True)
class ListBlock:
    ordered: bool
    start: int
    tight: bool
    items: list[ListItem]


@dataclass(slots=True)
class Table:
    header: list[list[Inline]]
    alignments: list[Align]
    rows: list[list[list[Inline]]]


@dataclass(slots=True)
class ThematicBreak:
    pass


@dataclass(slots=True)
class HtmlBlock:
    text: str


@dataclass(slots=True)
class Document:
    frontmatter: str | None
    blocks: list[Block]


@dataclass(slots=True)
class Text:
    text: str


@dataclass(slots=True)
class Em:
    inlines: list[Inline]


@dataclass(slots=True)
class Strong:
    inlines: list[Inline]


@dataclass(slots=True)
class CodeSpan:
    text: str


@dataclass(slots=True)
class Link:
    destination: str
    title: str | None
    inlines: list[Inline]


@dataclass(slots=True)
class Image:
    destination: str
    alt: str


@dataclass(slots=True)
class HardBreak:
    pass


@dataclass(slots=True)
class SoftBreak:
    pass


@dataclass(slots=True)
class HtmlInline:
    text: str


@dataclass(slots=True)
class Strike:
    inlines: list[Inline]


@dataclass(slots=True)
class Autolink:
    destination: str
    bare: bool


@dataclass(slots=True)
class Wikilink:
    target: str
    heading: str | None
    label: str | None


@dataclass(slots=True)
class Embed:
    target: str
    heading: str | None
    label: str | None


@dataclass(slots=True)
class Highlight:
    inlines: list[Inline]


Block = Heading | Paragraph | CodeBlock | Quote | ListBlock | Table | ThematicBreak | HtmlBlock
Inline = (
    Text
    | Em
    | Strong
    | CodeSpan
    | Link
    | Image
    | HardBreak
    | SoftBreak
    | HtmlInline
    | Strike
    | Autolink
    | Wikilink
    | Embed
    | Highlight
)
