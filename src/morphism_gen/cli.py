"""Command-line interface for morphism-gen."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from morphism_gen import __version__
from morphism_gen.config import (
    Config,
    ConfigError,
    TemplateSpec,
    load_config,
    resolve_input,
)
from morphism_gen.palette import FLAVOURS, MODES, SCHEME_VARIANTS, build_scheme
from morphism_gen.template import TemplateError, render

_WALLPAPER_ALIASES = ("wallpaper", "wall")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="morphism-gen",
        description="Generate application theme files from a wallpaper, using "
        "caelestia's exact Material You palette pipeline.",
    )
    parser.add_argument("wallpaper", type=Path, nargs="?", help="source wallpaper image")
    parser.add_argument("--version", action="version", version=f"morphism-gen {__version__}")
    parser.add_argument("--config", type=Path, help="path to config.toml")
    parser.add_argument(
        "--template",
        action="append",
        metavar="NAME",
        help="render only this template (repeatable); defaults to all configured",
    )
    parser.add_argument("--mode", choices=MODES, help="override the configured mode")
    parser.add_argument(
        "--variant",
        metavar="NAME",
        help=f"override the configured variant ({', '.join(SCHEME_VARIANTS)})",
    )
    parser.add_argument("--flavour", choices=FLAVOURS, help="override the configured flavour")
    parser.add_argument("--cache-dir", type=Path, help="directory for the extraction cache")
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="use a fresh temporary cache (matches the legacy script exactly)",
    )
    parser.add_argument("--json", action="store_true", help="print the scheme as JSON and exit")
    parser.add_argument("--lenient", action="store_true", help="leave unknown tokens verbatim")
    parser.add_argument("--list-templates", action="store_true", help="list configured templates")
    parser.add_argument("--print-config", action="store_true", help="print the effective config")
    return parser


def _default_cache_dir() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME") or "~/.cache"
    return Path(os.path.expanduser(xdg)) / "morphism-gen"


def _content_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def _run_post_hook(hook: str, spec: TemplateSpec, input_path, wallpaper: Path) -> None:
    command = hook
    replacements = {
        "{output}": str(spec.output),
        "{input}": str(input_path),
        "{wallpaper}": str(wallpaper),
    }
    for key, value in replacements.items():
        command = command.replace(key, value)

    result = subprocess.run(command, shell=True, check=False)
    if result.returncode != 0:
        print(
            f"morphism-gen: post_hook for '{spec.name}' exited with {result.returncode}",
            file=sys.stderr,
        )


def _select_templates(config: Config, names: list[str] | None) -> list[TemplateSpec]:
    if not names:
        return list(config.templates.values())

    selected = []
    for name in names:
        if name not in config.templates:
            available = ", ".join(config.templates) or "(none)"
            raise ConfigError(f"unknown template '{name}'; configured: {available}")
        selected.append(config.templates[name])
    return selected


def _prepare_cache(args, config: Config, wallpaper: Path):
    """Return (cache_path, keep_alive). keep_alive must stay referenced."""
    if args.no_cache:
        holder = tempfile.TemporaryDirectory(prefix="morphism-gen-")
        return Path(holder.name), holder

    base = args.cache_dir or config.cache_dir or _default_cache_dir()
    cache = base / _content_hash(wallpaper)[:16]
    cache.mkdir(parents=True, exist_ok=True)
    return cache, None


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"morphism-gen: {exc}", file=sys.stderr)
        return 1

    if args.mode:
        config.mode = args.mode
    if args.variant:
        config.variant = args.variant
    if args.flavour:
        config.flavour = args.flavour

    if args.list_templates:
        for name, spec in config.templates.items():
            location = spec.input if spec.input is not None else "(bundled)"
            print(f"{name}\t{location} -> {spec.output}")
        return 0

    if args.print_config:
        source = config.source_path or "(built-in default)"
        print(f"config: {source}")
        print(f"mode: {config.mode}")
        print(f"variant: {config.variant}")
        print(f"flavour: {config.flavour}")
        print(f"cache_dir: {config.cache_dir or _default_cache_dir()}")
        for name, spec in config.templates.items():
            location = spec.input if spec.input is not None else "(bundled)"
            print(f"template.{name}: {location} -> {spec.output}")
        return 0

    if args.wallpaper is None:
        print("morphism-gen: a wallpaper path is required", file=sys.stderr)
        return 2

    wallpaper = args.wallpaper.expanduser()
    if not wallpaper.is_file():
        print(f"morphism-gen: no such wallpaper: {wallpaper}", file=sys.stderr)
        return 1
    wallpaper = wallpaper.resolve()

    try:
        templates = _select_templates(config, args.template)
    except ConfigError as exc:
        print(f"morphism-gen: {exc}", file=sys.stderr)
        return 1

    cache, cache_holder = _prepare_cache(args, config, wallpaper)

    try:
        scheme = build_scheme(
            wallpaper,
            cache,
            mode=config.mode,
            variant=config.variant,
            flavour=config.flavour,
        )
    except Exception as exc:  # noqa: BLE001 - surface a clean CLI error
        print(f"morphism-gen: failed to extract palette: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(scheme.as_json()))
        return 0

    for spec in templates:
        try:
            input_path = resolve_input(spec)
        except ConfigError as exc:
            print(f"morphism-gen: {exc}", file=sys.stderr)
            return 1

        text = Path(input_path).read_text()
        try:
            rendered = render(text, scheme, strict=not args.lenient)
        except TemplateError as exc:
            print(f"morphism-gen: template '{spec.name}': {exc}", file=sys.stderr)
            return 1

        try:
            _write_atomic(spec.output, rendered)
        except OSError as exc:
            print(f"morphism-gen: could not write {spec.output}: {exc}", file=sys.stderr)
            return 1

        print(f"[{spec.name}] {input_path} -> {spec.output}")

        if spec.post_hook:
            _run_post_hook(spec.post_hook, spec, input_path, wallpaper)

    del cache_holder
    return 0
