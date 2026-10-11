# Disclaimer
This was entirely vibe-coded, this is a project meant purely for personal use
and is only a public GitHub repo because I wanted it to be a Nix flake without
too many abstractions.

# morphism-gen

A standalone, reusable Material You theme generator — similar in spirit to
[Matugen](https://github.com/InioX/matugen) and
[Wallust](https://codeberg.org/explosion-mental/wallust) — that reproduces
**caelestia-cli's** palette selection *exactly* and renders it into arbitrary
application config files via user-defined templates.

It is completely decoupled from any particular shell: the same binary can theme
Quickshell, Alacritty, Kitty, Foot, and anything else you can write a template
for.

## Colour accuracy

This is the core promise of the project. The extraction and scheme-generation
pipeline is **vendored verbatim** from caelestia-cli, so for identical inputs
and settings the output is byte-for-byte the same palette that caelestia-shell
produces. Matugen and Wallust use different preprocessing, quantizers, and
scoring, so they yield a different seed from the same wallpaper; morphism-gen
does not.

`tests/test_parity.py` locks this down: it replays the pre-refactor
`scripts/caelestia-theme.py` (frozen under `tests/legacy/`) and asserts the new
implementation returns *exactly* the same colours across every combination of
wallpaper pattern, mode, variant, and flavour.

## Dependencies

- Python ≥ 3.11 (uses `tomllib`)
- [`materialyoucolor`](https://pypi.org/project/materialyoucolor/) `>=3.0.4,<4`
- [`pillow`](https://pypi.org/project/pillow/) `>=12`

## Install

### Nix flake (recommended)

This repository is a flake. Run, build, or develop against it directly:

```sh
nix run github:roccoflac/morphism-gen -- --help   # run without installing
nix build github:roccoflac/morphism-gen           # ./result/bin/morphism-gen
nix develop github:roccoflac/morphism-gen         # dev shell (python + deps)
nix flake check github:roccoflac/morphism-gen     # runs the colour-parity suite
```

To install declaratively, add it as a flake input and reference the package.
In a NixOS/home-manager flake (e.g. `/etc/nixos/flake.nix`):

```nix
inputs.morphism-gen = {
  url = "github:roccoflac/morphism-gen";
  inputs.nixpkgs.follows = "nixpkgs";   # share the host's nixpkgs (see below)
};
```

then, in a home-manager module:

```nix
{ pkgs, morphism-gen, ... }:
{
  home.packages = [ morphism-gen.packages.${pkgs.system}.default ];
}
```

`inputs.nixpkgs.follows = "nixpkgs"` makes the flake use your host's nixpkgs, so
`materialyoucolor`, `pillow`, and the Python interpreter stay identical to the
ones the parity tests run against, with no duplicate nixpkgs closure.

### Run from source (no install)

If your interpreter already has the dependencies, run straight from the tree:

```sh
PYTHONPATH=src python3 -m morphism_gen --help
```

### Non-Nix systems

With a normal (non-externally-managed) Python, `pipx` or a virtualenv works:

```sh
pipx install .           # isolated, recommended
# or, in a venv:
python3 -m venv .venv && . .venv/bin/activate && pip install .
```

## Usage

Generate every configured template from a wallpaper:

```sh
morphism-gen /path/to/wallpaper.jpg
```

The default behaviour (no config file present) renders the bundled Quickshell
template to `~/.config/quickshell/services/ThemeService.qml`.

Common options:

```sh
morphism-gen <wallpaper> --mode dark --variant tonalspot --flavour hard
morphism-gen <wallpaper> --template alacritty          # only one template
morphism-gen <wallpaper> --json                        # print palette JSON, write nothing
morphism-gen --list-templates                          # show effective templates
morphism-gen --print-config                            # show resolved settings
morphism-gen <wallpaper> --no-cache                    # fresh temp cache (legacy behaviour)
```

| Option | Description |
| --- | --- |
| `--config PATH` | Use a specific config file. |
| `--template NAME` | Render only this template (repeatable). Default: all. |
| `--mode` | `smart` \| `dark` \| `light`. Overrides config. |
| `--variant` | `smart` \| `tonalspot` \| `content` \| `expressive` \| `fidelity` \| `fruitsalad` \| `monochrome` \| `neutral` \| `rainbow` \| `vibrant`. |
| `--flavour` | `default` \| `hard`. |
| `--cache-dir DIR` | Where to cache thumbnails/smart options. |
| `--no-cache` | Use a throwaway temp cache. |
| `--json` | Print `{mode, variant, source, colours}` and exit. |
| `--lenient` | Leave unknown template tokens in place instead of erroring. |
| `--list-templates` / `--print-config` | Introspection helpers. |

## Configuration

morphism-gen looks for a config file at `--config`, then
`$XDG_CONFIG_HOME/morphism-gen/config.toml`, then
`~/.config/morphism-gen/config.toml`. If none exists it uses a built-in default
with a single `quickshell` template.

```toml
[settings]
mode = "smart"                # smart | dark | light
variant = "smart"             # smart | tonalspot | content | ...
flavour = "default"           # default | hard
cache_dir = "~/.cache/morphism-gen"

[templates.quickshell]
# 'input' omitted -> use the bundled template named "quickshell"
output = "~/.config/quickshell/services/ThemeService.qml"

[templates.alacritty]
input = "~/.config/morphism-gen/templates/alacritty.toml"
output = "~/.config/alacritty/colours.toml"
post_hook = "pkill -USR1 alacritty"   # optional; {output} {input} {wallpaper}
```

- `input` may be omitted to use a bundled template with the same name.
- `output` is required for every template.
- Paths support `~` and environment-variable expansion.
- Writes are atomic (`.tmp` + rename).

## Bundled templates

| Name | Output kind |
| --- | --- |
| `quickshell` | Quickshell `ThemeService.qml` singleton |
| `alacritty` | Alacritty `colors.toml` include |
| `kitty` | Kitty `include` conf |
| `foot` | Foot `[colors]` ini |

## Template tokens

Templates are plain text with `{{ token }}` placeholders (whitespace inside the
braces is ignored). Alpha is expressed directly, e.g. `#{{outline}}33`.

**Metadata**

| Token | Result |
| --- | --- |
| `{{mode}}` | `dark` / `light` |
| `{{variant}}` | e.g. `tonalspot` |
| `{{flavour}}` | `default` / `hard` |
| `{{is_dark}}` | `true` / `false` |
| `{{wallpaper}}` | absolute wallpaper path |
| `{{source}}` / `{{source.hex}}` | seed hex, no `#` |
| `{{source.hash}}` | seed as `#rrggbb` |

**Colours** — one token per Material You role (`background`, `onSurface`,
`primary`, `primaryContainer`, … all 59 emitted roles):

| Token | Result |
| --- | --- |
| `{{primary}}` / `{{primary.hex}}` | `a4cce4` |
| `{{primary.hash}}` | `#a4cce4` |
| `{{primary.rgb}}` | `164, 204, 228` |
| `{{primary.argb}}` | `0xffa4cce4` |
| `{{primary.r}}` / `.g` / `.b` | single channel int |

Unknown tokens are a hard error unless `--lenient` is passed.

## Testing

No test dependencies beyond the runtime ones (`materialyoucolor`, `pillow`), so
they run directly on the Nix Python env:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -t tests -v
```

The same suite is wired up as a Nix check, so `nix flake check` enforces the
colour-parity guarantee in the sandbox:

```sh
nix flake check
```

## License

This project is licensed under the **GNU General Public License v3.0** (see
[`LICENSE`](LICENSE)). It incorporates code vendored from caelestia-cli, which
is GPL-3.0, so the combined work is GPL-3.0.

## Attribution

The colour engine (`colourfulness.py`, `material/score.py`,
`material/generator.py`) and the wallpaper helpers (`wallpaper.py`) are vendored
verbatim from **caelestia-cli** at commit
`82039823c0d538f8fcaf18a1636bf244bd583da7`, which is licensed under the GNU
General Public License v3.0. Everything else is original to this project.
