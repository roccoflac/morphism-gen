"""Configuration loading for morphism-gen.

Configuration lives in a TOML file. It is discovered in this order:

1. an explicit ``--config PATH``
2. ``$XDG_CONFIG_HOME/morphism-gen/config.toml``
3. ``~/.config/morphism-gen/config.toml``
4. the built-in default (a single ``quickshell`` template)

Schema::

    [settings]
    mode = "smart"           # smart | dark | light
    variant = "smart"        # smart | tonalspot | content | ...
    flavour = "default"      # default | hard
    cache_dir = "~/.cache/morphism-gen"

    [templates.quickshell]
    # 'input' omitted -> use the bundled template named "quickshell"
    output = "~/.config/quickshell/services/ThemeService.qml"
    # post_hook = "hyprctl reload"   # optional; {output} {input} {wallpaper}

    [templates.alacritty]
    input = "~/.config/morphism-gen/templates/alacritty.toml"
    output = "~/.config/alacritty/colours.toml"
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from importlib.resources import files as _resource_files

APP_NAME = "morphism-gen"

DEFAULT_CONFIG_TOML = """\
[settings]
mode = "smart"
variant = "smart"
flavour = "default"

[templates.quickshell]
output = "~/.config/quickshell/services/ThemeService.qml"
"""


class ConfigError(Exception):
    """Raised for an unreadable or invalid configuration."""


@dataclass(frozen=True)
class TemplateSpec:
    name: str
    output: Path
    input: Path | None = None
    post_hook: str | None = None


@dataclass
class Config:
    mode: str = "smart"
    variant: str = "smart"
    flavour: str = "default"
    cache_dir: Path | None = None
    templates: dict[str, TemplateSpec] = field(default_factory=dict)
    source_path: Path | None = None


def _expand(value: str) -> Path:
    return Path(os.path.expanduser(os.path.expandvars(value)))


def bundled_templates_dir():
    return _resource_files("morphism_gen").joinpath("templates")


def find_bundled(name: str):
    """Return the bundled template file for ``name`` (stem match), or None."""
    directory = bundled_templates_dir()
    matches = [entry for entry in directory.iterdir() if entry.name.rsplit(".", 1)[0] == name]
    if not matches:
        return None
    if len(matches) > 1:
        names = ", ".join(sorted(m.name for m in matches))
        raise ConfigError(f"bundled template '{name}' is ambiguous: {names}")
    return matches[0]


def default_config() -> Config:
    data = tomllib.loads(DEFAULT_CONFIG_TOML)
    return _from_mapping(data, source_path=None)


def config_search_paths() -> list[Path]:
    xdg = os.environ.get("XDG_CONFIG_HOME") or "~/.config"
    return [_expand(xdg) / APP_NAME / "config.toml"]


def discover_config_path() -> Path | None:
    for candidate in config_search_paths():
        if candidate.is_file():
            return candidate
    return None


def load_config(path: Path | str | None = None) -> Config:
    """Load configuration, falling back to the built-in default."""
    if path is not None:
        config_path = Path(path).expanduser()
        if not config_path.is_file():
            raise ConfigError(f"config file not found: {config_path}")
    else:
        config_path = discover_config_path()

    if config_path is None:
        return default_config()

    try:
        with config_path.open("rb") as handle:
            data = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {config_path}: {exc}") from exc

    return _from_mapping(data, source_path=config_path)


def _from_mapping(data: dict, source_path: Path | None) -> Config:
    settings = data.get("settings", {})
    if not isinstance(settings, dict):
        raise ConfigError("[settings] must be a table")

    config = Config(source_path=source_path)

    if "mode" in settings:
        config.mode = str(settings["mode"])
    if "variant" in settings:
        config.variant = str(settings["variant"])
    if "flavour" in settings:
        config.flavour = str(settings["flavour"])
    if "cache_dir" in settings:
        config.cache_dir = _expand(str(settings["cache_dir"]))

    templates = data.get("templates", {})
    if not isinstance(templates, dict):
        raise ConfigError("[templates] must be a table")

    for name, spec in templates.items():
        if not isinstance(spec, dict):
            raise ConfigError(f"[templates.{name}] must be a table")
        if "output" not in spec:
            raise ConfigError(f"[templates.{name}] is missing 'output'")
        config.templates[name] = TemplateSpec(
            name=name,
            output=_expand(str(spec["output"])),
            input=_expand(str(spec["input"])) if spec.get("input") else None,
            post_hook=str(spec["post_hook"]) if spec.get("post_hook") else None,
        )

    if not config.templates:
        raise ConfigError("no [templates.*] defined in configuration")

    return config


def resolve_input(spec: TemplateSpec) -> "object":
    """Resolve a template spec's input to a readable file path.

    Explicit inputs must exist. Otherwise the bundled template matching the
    spec name is used.
    """
    if spec.input is not None:
        if not spec.input.is_file():
            raise ConfigError(f"template '{spec.name}': input not found: {spec.input}")
        return spec.input

    bundled = find_bundled(spec.name)
    if bundled is None:
        raise ConfigError(
            f"template '{spec.name}': no input given and no bundled template named '{spec.name}'"
        )
    return bundled
