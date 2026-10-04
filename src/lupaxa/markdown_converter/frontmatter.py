"""Split a leading YAML frontmatter fence from the rest of the text."""

from __future__ import annotations


def _line_without_newline(line: str) -> str:
    return line.rstrip("\r\n")


def split_frontmatter(text: str) -> tuple[str | None, str]:
    """Return the raw leading fence and the unmodified remainder.

    A fence exists only when the first line is exactly ``---`` and a later
    line is exactly ``---``. Both fence lines keep their original newlines.
    """
    lines = text.splitlines(keepends=True)
    if not lines or _line_without_newline(lines[0]) != "---":
        return None, text
    for index in range(1, len(lines)):
        if _line_without_newline(lines[index]) == "---":
            front = "".join(lines[: index + 1])
            body = "".join(lines[index + 1 :])
            return front, body
    return None, text
