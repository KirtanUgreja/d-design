"""Edits that need no model (docs/v4/plan/28-editor.md): a field's words
changed inside an already composed slide. The composition stays; QA runs
again on the result (the worker's edit job), and a slide the new words break
is flagged with "Fit to slide" offered, never saved silently broken.
"""

from __future__ import annotations

from html import escape
from html.parser import HTMLParser

_VOID = frozenset({"br", "hr", "img", "input", "meta", "link", "wbr"})


class _Finder(HTMLParser):
    """The character span of the element carrying data-field=name: from the
    end of its start tag to the start of its end tag, nesting counted."""

    def __init__(self, name: str) -> None:
        super().__init__(convert_charrefs=False)
        self.name = name
        self.depth = 0  # > 0 while inside the field
        self.start = -1
        self.end = -1
        self._lines: list[int] = [0]  # character offset where each line starts

    def _offset(self) -> int:
        line, col = self.getpos()
        return self._lines[line - 1] + col

    def feed_all(self, html: str) -> None:
        self._lines = [0]
        for line in html.splitlines(keepends=True):
            self._lines.append(self._lines[-1] + len(line))
        self.feed(html)
        self.close()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _VOID:
            return
        if self.depth:
            self.depth += 1
        elif self.start < 0 and dict(attrs).get("data-field") == self.name:
            text = self.get_starttag_text() or ""
            self.start = self._offset() + len(text)
            self.depth = 1

    def handle_endtag(self, tag: str) -> None:
        if tag in _VOID or not self.depth:
            return
        self.depth -= 1
        if self.depth == 0 and self.end < 0:
            self.end = self._offset()


def set_field(html: str, name: str, text: str) -> str | None:
    """The slide with one field's words replaced (escaped; any emphasis the
    composition put inside the field goes with the old words). None when the
    slide has no such field."""
    finder = _Finder(name)
    finder.feed_all(html)
    if finder.start < 0 or finder.end < 0:
        return None
    return html[: finder.start] + escape(text) + html[finder.end :]
