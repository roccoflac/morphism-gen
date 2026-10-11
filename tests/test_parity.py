"""Colour-accuracy parity tests.

These are the single most important tests in the project: they assert that the
refactored generator produces *exactly* the same colours as the pre-refactor
``scripts/caelestia-theme.py`` for identical inputs and settings.

The frozen copy of the legacy implementation lives in ``tests/legacy/`` and is
never modified.
"""

import tempfile
import unittest
from pathlib import Path

import support  # noqa: F401  (sets up sys.path)
from PIL import Image

import legacy_cli
from morphism_gen.palette import ColourScheme, build_scheme
from morphism_gen.template import render

MODES = ("smart", "dark", "light")
VARIANTS = ("smart", "tonalspot", "content", "expressive", "fidelity")
FLAVOURS = ("default", "hard")


def make_wallpaper(path: Path, pattern: str) -> None:
    size = 64
    img = Image.new("RGB", (size, size))
    pixels = img.load()
    for y in range(size):
        for x in range(size):
            if pattern == "gradient":
                pixels[x, y] = ((x * 4) % 256, (y * 4) % 256, ((x + y) * 2) % 256)
            elif pattern == "warm":
                pixels[x, y] = (200, (x * 3) % 100 + 40, (y * 2) % 60)
            elif pattern == "mono":
                value = (x + y) % 256
                pixels[x, y] = (value, value, value)
            elif pattern == "flat":
                pixels[x, y] = (120, 150, 170)
            else:  # pragma: no cover - defensive
                raise ValueError(pattern)
    img.save(path)


def bundled_template() -> Path:
    from morphism_gen.config import find_bundled

    template = find_bundled("quickshell")
    assert template is not None
    return Path(template)


class ColourParityTest(unittest.TestCase):
    def test_colours_match_legacy_exactly(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for pattern in ("gradient", "warm", "mono", "flat"):
                wall = base / f"{pattern}.png"
                make_wallpaper(wall, pattern)

                for mode in MODES:
                    for variant in VARIANTS:
                        for flavour in FLAVOURS:
                            with self.subTest(pattern=pattern, mode=mode, variant=variant, flavour=flavour):
                                legacy_colours, legacy_mode, legacy_variant, legacy_seed = legacy_cli.build(
                                    wall, mode, variant, flavour
                                )

                                cache = base / "cache" / f"{pattern}-{mode}-{variant}-{flavour}"
                                scheme = build_scheme(
                                    wall, cache, mode=mode, variant=variant, flavour=flavour
                                )

                                self.assertEqual(legacy_colours, scheme.colours)
                                self.assertEqual(legacy_mode, scheme.mode)
                                self.assertEqual(legacy_variant, scheme.variant)
                                self.assertEqual(legacy_seed, scheme.source)


class QmlGoldenTest(unittest.TestCase):
    def test_bundled_qml_matches_legacy_render_except_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            wall = Path(tmp) / "wall.png"
            make_wallpaper(wall, "gradient")

            colours, mode, variant, seed = legacy_cli.build(wall, "dark", "tonalspot", "default")
            legacy_qml = legacy_cli.render_qml(colours, mode, variant, seed, "default")

            scheme = ColourScheme(
                colours=colours,
                mode=mode,
                variant=variant,
                flavour="default",
                source=seed,
                wallpaper=wall,
            )
            new_qml = render(bundled_template().read_text(), scheme)

            legacy_lines = legacy_qml.splitlines()
            new_lines = new_qml.splitlines()

            self.assertEqual(legacy_lines[1:], new_lines[1:])


if __name__ == "__main__":
    unittest.main()
