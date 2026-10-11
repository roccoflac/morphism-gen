"""Palette extraction: wallpaper -> Material You colour scheme.

This orchestrates the vendored engine. The order of operations mirrors the
original ``build()`` in ``scripts/caelestia-theme.py`` exactly:

1. build/read the 128x128 NEAREST thumbnail
2. resolve "smart" mode and variant from that thumbnail
3. score the thumbnail to obtain the seed colour
4. generate the scheme from the seed

Because steps 1-4 are unchanged, the resulting colours are identical.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from morphism_gen.material.generator import gen_scheme
from morphism_gen.material.score import score
from morphism_gen.wallpaper import get_smart_opts, get_thumb

SCHEME_VARIANTS = (
    "tonalspot",
    "content",
    "expressive",
    "fidelity",
    "fruitsalad",
    "monochrome",
    "neutral",
    "rainbow",
    "vibrant",
)

MODES = ("smart", "dark", "light")
FLAVOURS = ("default", "hard")


@dataclass(frozen=True)
class ColourScheme:
    """A generated palette plus the resolved settings that produced it."""

    colours: dict[str, str]
    mode: str
    variant: str
    flavour: str
    source: str
    wallpaper: Path

    def as_json(self) -> dict:
        return {
            "mode": self.mode,
            "variant": self.variant,
            "source": self.source,
            "colours": self.colours,
        }


def build_scheme(
    wallpaper: Path,
    cache: Path,
    mode: str = "smart",
    variant: str = "smart",
    flavour: str = "default",
) -> ColourScheme:
    """Run the caelestia pipeline and return the resolved colour scheme."""
    wall = Path(wallpaper).resolve()
    thumb = get_thumb(wall, cache)

    if mode == "smart" or variant == "smart":
        smart = get_smart_opts(wall, cache)
        if mode == "smart":
            mode = smart["mode"]
        if variant == "smart":
            variant = smart["variant"]

    scheme = SimpleNamespace(name="dynamic", flavour=flavour, mode=mode, variant=variant)
    primary = score(str(thumb))
    colours = gen_scheme(scheme, primary)

    seed_hex = f"{primary.to_int() & 0xFFFFFF:06x}"

    return ColourScheme(
        colours=colours,
        mode=mode,
        variant=variant,
        flavour=flavour,
        source=seed_hex,
        wallpaper=wall,
    )
