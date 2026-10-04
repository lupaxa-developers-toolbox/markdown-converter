"""Obsidian inline rules for wikilinks, embeds, and highlights."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from markdown_it.rules_inline.state_inline import Delimiter, StateInline

if TYPE_CHECKING:
    from markdown_it import MarkdownIt

_WIKILINK_RE = re.compile(r"(!?)\[\[([^\]\n]+)\]\]")


def register_obsidian(md: MarkdownIt) -> None:
    """Register wikilink and highlight rules on an Obsidian parser."""
    md.inline.ruler.before("image", "wikilink", _wikilink)
    md.inline.ruler.before("emphasis", "highlight", _highlight)
    md.inline.ruler2.after("strikethrough", "highlight", _highlight_post)


def _wikilink(state: StateInline, silent: bool) -> bool:
    if state.pos >= state.posMax:
        return False
    match = _WIKILINK_RE.match(state.src, state.pos)
    if match is None:
        return False
    if not silent:
        name = "embed" if match.group(1) else "wikilink"
        token = state.push(name, "", 0)
        token.content = match.group(2)
    state.pos += len(match.group(0))
    return True


def _highlight(state: StateInline, silent: bool) -> bool:
    """Treat ``==`` like markdown-it's ``~~`` strikethrough. A single ``=`` is text."""
    if silent:
        return False
    if state.pos >= state.posMax or state.src[state.pos] != "=":
        return False

    scanned = state.scanDelims(state.pos, True)
    length = scanned.length
    if length < 2:
        return False

    if length % 2:
        token = state.push("text", "", 0)
        token.content = "="
        length -= 1

    index = 0
    while index < length:
        token = state.push("text", "", 0)
        token.content = "=="
        state.delimiters.append(
            Delimiter(
                marker=ord("="),
                length=0,
                token=len(state.tokens) - 1,
                end=-1,
                open=scanned.can_open,
                close=scanned.can_close,
            )
        )
        index += 2

    state.pos += scanned.length
    return True


def _highlight_post(state: StateInline) -> None:
    _pair_marks(state, state.delimiters)
    for meta in state.tokens_meta:
        if meta and "delimiters" in meta:
            _pair_marks(state, meta["delimiters"])


def _pair_marks(state: StateInline, delimiters: list[Delimiter]) -> None:
    lone_markers: list[int] = []
    index = 0
    while index < len(delimiters):
        start = delimiters[index]
        if start.marker != 0x3D or start.end == -1:
            index += 1
            continue

        end = delimiters[start.end]
        markup = state.tokens[start.token].content

        opener = state.tokens[start.token]
        opener.type = "mark_open"
        opener.tag = "mark"
        opener.nesting = 1
        opener.markup = markup
        opener.content = ""

        closer = state.tokens[end.token]
        closer.type = "mark_close"
        closer.tag = "mark"
        closer.nesting = -1
        closer.markup = markup
        closer.content = ""

        previous = end.token - 1
        if (
            previous >= 0
            and state.tokens[previous].type == "text"
            and state.tokens[previous].content == "="
        ):
            lone_markers.append(previous)
        index += 1

    while lone_markers:
        start_at = lone_markers.pop()
        shift_to = start_at + 1
        while shift_to < len(state.tokens) and state.tokens[shift_to].type == "mark_close":
            shift_to += 1
        shift_to -= 1
        if start_at != shift_to:
            state.tokens[shift_to], state.tokens[start_at] = (
                state.tokens[start_at],
                state.tokens[shift_to],
            )
