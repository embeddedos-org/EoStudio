# EoStudio — Universal Development & Design Platform

[![CI](https://github.com/embeddedos-org/EoStudio/actions/workflows/ci.yml/badge.svg)](https://github.com/embeddedos-org/EoStudio/actions/workflows/ci.yml)
[![CodeQL](https://github.com/embeddedos-org/EoStudio/actions/workflows/codeql.yml/badge.svg)](https://github.com/embeddedos-org/EoStudio/actions/workflows/codeql.yml)
[![Scorecard](https://github.com/embeddedos-org/EoStudio/actions/workflows/scorecard.yml/badge.svg)](https://github.com/embeddedos-org/EoStudio/actions/workflows/scorecard.yml)
[![Release](https://github.com/embeddedos-org/EoStudio/actions/workflows/release.yml/badge.svg)](https://github.com/embeddedos-org/EoStudio/actions/workflows/release.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

EoStudio is a Python development and design platform for the **EmbeddedOS (EoS)**
ecosystem. It combines a visual editor/design suite with multi-target code
generation, 2D/3D asset export, AI-assisted coding, real-time collaboration, and
a plugin system, driven from a single `EoStudio` command-line entry point
(`click`-based). It is part of the
[EmbeddedOS (EoS)](https://github.com/embeddedos-org) ecosystem and integrates
with [eOffice](https://github.com/embeddedos-org/eOffice) and
[EoSim](https://github.com/embeddedos-org/EoSim) through bundled plugins.
Version 3.1.0.

## Building EmbeddedOS projects

EoStudio is a front end for [ebuild](https://github.com/embeddedos-org/ebuild),
the platform's build control plane — it drives ebuild rather than reimplementing
what ebuild does.

A project containing a `build.yaml` is recognised as an ebuild project and built
through the real CLI:

| Action | Command |
|---|---|
| Build | `ebuild build` |
| Test | `ebuild test` |
| Clean | `ebuild clean` |
| Run | `ebuild monitor` |

The board is selected separately, by `ebuild configure --board <board>`; there
is no top-level `--platform` or `--config` flag.

`build.yaml` is matched ahead of every other marker on purpose. ebuild generates
its build files into the build directory, so a project that has been configured
once carries a `CMakeLists.txt` as well — matching CMake first would hand the
project to a backend that bypasses the toolchain that owns it.

The generic backends below (npm, Cargo, Gradle and the rest) remain available
for ordinary projects opened in the IDE. They are not used for EmbeddedOS
targets.

## What's inside

| Path | Contents |
|---|---|
| `eostudio/cli/` | The `EoStudio` command-line interface |
| `eostudio/core/ai/` | Model router, orchestrator, inline completion, agentic coder, workspace intelligence |
| `eostudio/core/collaboration/` | Real-time multi-user editing (Operational Transformation) |
| `eostudio/core/ide/` | Code intelligence (`code_intelligence`) |
| `eostudio/core/devtools/` | Git / CI / Docker developer tooling (`devex`) |
| `eostudio/core/security/` | Static analysis and secret scanning (`hardening`) |
| `eostudio/core/` (more) | `ui`, `ui_flow`, `animation`, `geometry`, `prototyping`, `scaffold`, `simulation`, `deploy`, `specs`, `uml`, `video`, `enterprise` |
| `eostudio/codegen/` | Code generators: React, Flutter, HTML/CSS, WASM, GTK, .NET, mobile, game engine, hardware, OpenSCAD, device tree |
| `eostudio/formats/` | 2D/3D export: SVG, DXF, STL, OBJ, glTF |
| `eostudio/gui/` | Desktop GUI (`app`, `editors`, `widgets`, `dialogs`) |
| `eostudio/platform/` | Rendering backends: Tkinter, web, PWA, Electron, macOS, EoS |
| `eostudio/plugins/` | Plugin base + marketplace; `eoffice` and `eosim` plugins |
| `eostudio/templates/` | Project and sample templates |
| `tests/` | pytest suite |

## Install

```bash
git clone https://github.com/embeddedos-org/EoStudio.git
cd EoStudio
pip install -e ".[dev]"
EoStudio --help
```

The base install pulls only `click`. AI and integration features are opt-in
extras:

| Extra | Adds |
|---|---|
| `.[ai]` | OpenAI model backend (`httpx`, `tiktoken`, `openai`) |
| `.[ai-full]` | `ai` plus Anthropic |
| `.[ai-local]` | Local/Ollama backend via `httpx` |
| `.[database]` | PostgreSQL, MySQL, MongoDB, Redis clients |
| `.[cloud]` | `httpx`, `keyring` |
| `.[video]` | `edge-tts` (narrated release videos) |
| `.[all]` | Everything above |

## Test

```bash
pip install -e ".[dev]"
pytest        # tests/ (configured in pyproject.toml)
```

## Docs

See [`docs/`](docs/) (`mkdocs.yml`) and [`CHANGELOG.md`](CHANGELOG.md).

## License

Licensed under the [MIT License](LICENSE).
