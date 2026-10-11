import unittest
from pathlib import Path

import support  # noqa: F401  (sets up sys.path)

from morphism_gen.palette import ColourScheme
from morphism_gen.template import TemplateError, render


def scheme(mode: str = "dark") -> ColourScheme:
    return ColourScheme(
        colours={"primary": "a4cce4", "onPrimary": "1b4459", "outline": "6f767c"},
        mode=mode,
        variant="tonalspot",
        flavour="default",
        source="7897aa",
        wallpaper=Path("/tmp/wall.png"),
    )


class ColourTokenTest(unittest.TestCase):
    def test_default_and_hex(self):
        self.assertEqual(render("{{primary}}", scheme()), "a4cce4")
        self.assertEqual(render("{{primary.hex}}", scheme()), "a4cce4")
        self.assertEqual(render("{{ primary.hex }}", scheme()), "a4cce4")

    def test_hash(self):
        self.assertEqual(render("{{primary.hash}}", scheme()), "#a4cce4")

    def test_rgb(self):
        self.assertEqual(render("{{primary.rgb}}", scheme()), "164, 204, 228")
        self.assertEqual(render("{{primary.r}}", scheme()), "164")
        self.assertEqual(render("{{primary.g}}", scheme()), "204")
        self.assertEqual(render("{{primary.b}}", scheme()), "228")

    def test_argb(self):
        self.assertEqual(render("{{primary.argb}}", scheme()), "0xffa4cce4")

    def test_alpha_is_template_level(self):
        self.assertEqual(render("#{{outline}}33", scheme()), "#6f767c33")


class MetadataTokenTest(unittest.TestCase):
    def test_metadata(self):
        self.assertEqual(render("{{mode}}", scheme("dark")), "dark")
        self.assertEqual(render("{{variant}}", scheme()), "tonalspot")
        self.assertEqual(render("{{flavour}}", scheme()), "default")
        self.assertEqual(render("{{wallpaper}}", scheme()), "/tmp/wall.png")

    def test_is_dark(self):
        self.assertEqual(render("{{is_dark}}", scheme("dark")), "true")
        self.assertEqual(render("{{is_dark}}", scheme("light")), "false")

    def test_source(self):
        self.assertEqual(render("{{source}}", scheme()), "7897aa")
        self.assertEqual(render("{{source.hash}}", scheme()), "#7897aa")
        self.assertEqual(render("{{source_colour}}", scheme()), "7897aa")


class ErrorTest(unittest.TestCase):
    def test_unknown_token_strict(self):
        with self.assertRaises(TemplateError):
            render("{{nope}}", scheme())

    def test_unknown_token_lenient(self):
        self.assertEqual(render("{{nope}}", scheme(), strict=False), "{{nope}}")

    def test_unknown_format_strict(self):
        with self.assertRaises(TemplateError):
            render("{{primary.wat}}", scheme())


if __name__ == "__main__":
    unittest.main()
