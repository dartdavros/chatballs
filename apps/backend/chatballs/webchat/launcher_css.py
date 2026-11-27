"""Select the styles that may run in the launcher's isolated shadow root."""

import re

import tinycss2

_BUTTON = r"\.(?:cb-launcher|chatballs-chat-launcher)"
_STATE = r"(?::(?:hover|active|focus|focus-visible|disabled))*"
_CHILD = r"(?:(?:\s+|\s*>\s*)(?:img|svg|\.chatballs-chat-(?:eyes|dot)))?"
_PSEUDO = r"(?:::(?:before|after))?"
_SELECTOR = re.compile(_BUTTON + _STATE + _CHILD + _STATE + _PSEUDO)
_PROPERTIES = set("""
    background background-color background-image background-size background-position background-repeat
    color border border-width border-style border-color border-radius
    border-top border-right border-bottom border-left box-shadow
    width height min-width min-height max-width max-height padding margin
    display align-items justify-content gap
    font font-size font-weight font-family line-height letter-spacing text-shadow
    outline outline-color outline-offset outline-style outline-width
    fill stroke stroke-width opacity transform transition filter
    object-fit object-position content
""".split())
_FUNCTIONS = {
    "calc", "min", "max", "clamp", "var", "rgb", "rgba", "hsl", "hsla", "oklch", "oklab", "color",
    "color-mix", "linear-gradient", "radial-gradient", "conic-gradient",
    "repeating-linear-gradient", "repeating-radial-gradient", "repeating-conic-gradient",
    "translate", "translatex", "translatey", "scale", "scalex", "scaley", "rotate", "skew",
    "drop-shadow", "brightness", "contrast", "saturate", "grayscale", "blur",
}


def _safe_values(tokens, *, depth=0):
    if depth > 8:
        return False
    for token in tokens:
        if token.type == "url":
            if not token.value.lower().startswith("data:image/"):
                return False
        elif token.type == "function":
            if token.lower_name == "url":
                args = [arg for arg in token.arguments if arg.type != "whitespace"]
                if len(args) != 1 or args[0].type != "string" or not args[0].value.lower().startswith("data:image/"):
                    return False
            elif token.lower_name not in _FUNCTIONS or not _safe_values(token.arguments, depth=depth + 1):
                return False
        elif token.type not in {"ident", "hash", "string", "whitespace", "number", "dimension", "percentage", "literal"}:
            return False
    return True


def launcher_css(css: str) -> str:
    """Restrict selectors and styling to the widget button, with no external assets."""
    output = []
    for rule in tinycss2.parse_stylesheet(css, skip_comments=True, skip_whitespace=True):
        if rule.type != "qualified-rule":
            continue
        selectors = [selector.strip() for selector in tinycss2.serialize(rule.prelude).split(",")]
        buttons = [selector for selector in selectors if _SELECTOR.fullmatch(selector)]
        if not buttons:
            continue
        declarations = []
        for declaration in tinycss2.parse_declaration_list(rule.content, skip_comments=True, skip_whitespace=True):
            if (declaration.type == "declaration" and declaration.lower_name in _PROPERTIES
                    and _safe_values(declaration.value)):
                declarations.append(declaration.serialize() + ";")
        if declarations:
            output.append(",".join(buttons) + "{" + "".join(declarations) + "}")
    return "\n".join(output)
