from __future__ import annotations

import html
from html.parser import HTMLParser
from urllib.parse import urlsplit

_ALLOWED_TAGS = {
    "a",
    "b",
    "blockquote",
    "br",
    "code",
    "div",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "li",
    "ol",
    "p",
    "pre",
    "s",
    "span",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "u",
    "ul",
}
_BLOCKED_TAGS = {
    "applet",
    "audio",
    "button",
    "embed",
    "form",
    "head",
    "iframe",
    "input",
    "link",
    "meta",
    "object",
    "script",
    "select",
    "style",
    "svg",
    "textarea",
    "title",
    "video",
}
_VOID_TAGS = {"br", "hr"}


def _safe_href(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        return ""
    parsed = urlsplit(candidate)
    if parsed.scheme.lower() not in {"http", "https", "mailto"}:
        return ""
    return candidate


class _Sanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.blocked_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in _BLOCKED_TAGS:
            self.blocked_depth += 1
            return
        if self.blocked_depth or tag not in _ALLOWED_TAGS:
            return
        safe_attrs: list[str] = []
        if tag == "a":
            href = next((value or "" for key, value in attrs if key.lower() == "href"), "")
            href = _safe_href(href)
            if href:
                safe_attrs.extend(
                    [
                        f'href="{html.escape(href, quote=True)}"',
                        'target="_blank"',
                        'rel="noopener noreferrer"',
                    ]
                )
        suffix = f" {' '.join(safe_attrs)}" if safe_attrs else ""
        self.parts.append(f"<{tag}{suffix}>")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _BLOCKED_TAGS:
            self.blocked_depth = max(0, self.blocked_depth - 1)
            return
        if self.blocked_depth or tag not in _ALLOWED_TAGS or tag in _VOID_TAGS:
            return
        self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if not self.blocked_depth:
            self.parts.append(html.escape(data))


def sanitize_email_html(markup: str) -> str:
    parser = _Sanitizer()
    parser.feed(markup)
    parser.close()
    return "".join(parser.parts).strip()
