"""Wallpaper preprocessing, copied verbatim from caelestia-cli.

The two functions here are the exact ones used by caelestia-shell to turn a
wallpaper into a thumbnail and to derive the "smart" mode/variant. They are
kept byte-for-byte equivalent so that the derived seed is identical.

Source: caelestia-cli `82039823c0d538f8fcaf18a1636bf244bd583da7`
  - `utils/wallpaper.py` (``get_thumb`` / ``get_smart_opts``)
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image
from materialyoucolor.hct import Hct
from materialyoucolor.utils.color_utils import argb_from_rgb

from morphism_gen.colourfulness import get_variant


def get_thumb(wall: Path, cache: Path) -> Path:
    thumb = cache / "thumbnail.jpg"

    if not thumb.exists():
        with Image.open(wall) as img:
            img = img.convert("RGB")
            img.thumbnail((128, 128), Image.Resampling.NEAREST)
            thumb.parent.mkdir(parents=True, exist_ok=True)
            img.save(thumb, "JPEG")

    return thumb


def get_smart_opts(wall: Path, cache: Path) -> dict:
    opts_cache = cache / "smart.json"

    try:
        return json.loads(opts_cache.read_text())
    except (IOError, json.JSONDecodeError):
        pass

    opts = {}

    with Image.open(get_thumb(wall, cache)) as img:
        opts["variant"] = get_variant(img)
        img.thumbnail((1, 1), Image.Resampling.LANCZOS)
        pixel = img.getpixel((0, 0))
        hct = Hct.from_int(argb_from_rgb(*pixel))
        opts["mode"] = "light" if hct.tone > 60 else "dark"

    opts_cache.parent.mkdir(parents=True, exist_ok=True)
    opts_cache.write_text(json.dumps(opts))

    return opts
