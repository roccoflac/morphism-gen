"""A tiny, dependency-free template renderer.

Templates are plain text containing ``{{ token }}`` placeholders. Whitespace
inside the braces is ignored. The token grammar is intentionally small:

Metadata tokens
    {{mode}}            resolved mode, e.g. ``dark``
    {{variant}}         resolved variant, e.g. ``tonalspot``
    {{flavour}}         ``default`` or ``hard``
    {{is_dark}}         ``true`` / ``false``
    {{wallpaper}}       absolute path to the source wallpaper
    {{source}}          seed colour as 6-digit hex, no ``#``
    {{source.hex}}      alias of ``{{source}}``
    {{source.hash}}     seed colour as ``#rrggbb``

Colour tokens (one per Material You role, e.g. ``primary``, ``onSurface``)
    {{primary}}         / {{primary.hex}}   -> ``a4cce4``
    {{primary.hash}}                        -> ``#a4cce4``
    {{primary.rgb}}                         -> ``164, 204, 228``
    {{primary.argb}}                        -> ``0xffa4cce4``
    {{primary.r}} / {{primary.g}} / {{primary.b}} -> single channel int

Alpha is a template concern: write ``#{{outline}}33`` for a 20% outline.

Unknown tokens raise :class:`TemplateError` unless ``strict=False`` is passed
to :func:`render`, in which case they are left in place verbatim.
"""

from __future__ import annotations

import re

from morphism_gen.palette import ColourScheme

_TOKEN_RE = re.compile(r"\{\{\s*([^{}]*?)\s*\}\}")

_COLOUR_FORMATS = {"hex", "hash", "rgb", "argb", "r", "g", "b"}
_SOURCE_FORMATS = {"hex", "hash"}
_FALSEY = {"", "0", "false", "no", "off"}


class TemplateError(Exception):
    """Raised for an invalid or unresolvable template token."""


def _channels(hex_value: str) -> tuple[int, int, int]:
    return int(hex_value[0:2], 16), int(hex_value[2:4], 16), int(hex_value[4:6], 16)


def _format_colour(hex_value: str, fmt: str) -> str:
    if fmt in ("hex",):
        return hex_value
    if fmt == "hash":
        return f"#{hex_value}"
    r, g, b = _channels(hex_value)
    if fmt == "rgb":
        return f"{r}, {g}, {b}"
    if fmt == "argb":
        return f"0xff{hex_value}"
    if fmt == "r":
        return str(r)
    if fmt == "g":
        return str(g)
    if fmt == "b":
        return str(b)
    raise TemplateError(f"unknown colour format '.{fmt}'")


class TokenContext:
    """Resolves template tokens against a concrete :class:`ColourScheme`."""

    def __init__(self, scheme: ColourScheme):
        self.scheme = scheme
        self._meta = {
            "mode": scheme.mode,
            "variant": scheme.variant,
            "flavour": scheme.flavour,
            "is_dark": "false" if scheme.mode == "light" else "true",
            "wallpaper": str(scheme.wallpaper),
        }

    def resolve(self, token: str) -> str:
        if not token:
            raise TemplateError("empty token")

        if token in self._meta:
            return self._meta[token]

        name, _, fmt = token.partition(".")

        if name in ("source", "source_colour"):
            fmt = fmt or "hex"
            if fmt not in _SOURCE_FORMATS:
                raise TemplateError(f"unknown format '.{fmt}' for {name}")
            return self.scheme.source if fmt == "hex" else f"#{self.scheme.source}"

        if name in self.scheme.colours:
            fmt = fmt or "hex"
            if fmt not in _COLOUR_FORMATS:
                raise TemplateError(f"unknown format '.{fmt}' for colour {name}")
            return _format_colour(self.scheme.colours[name], fmt)

        raise TemplateError(f"unknown token '{token}'")


def render(text: str, scheme: ColourScheme, strict: bool = True) -> str:
    """Render ``text``, substituting tokens resolved from ``scheme``."""
    context = TokenContext(scheme)
    return _TOKEN_RE.sub(lambda m: _sub(m, context, strict), text)


def _sub(match: re.Match[str], context: TokenContext, strict: bool) -> str:
    token = match.group(1)
    try:
        return context.resolve(token)
    except TemplateError:
        if strict:
            raise
        return match.group(0)


def render_file(path, scheme: ColourScheme, strict: bool = True) -> str:
    from pathlib import Path

    return render(Path(path).read_text(), scheme, strict=strict)
