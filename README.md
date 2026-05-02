# EoStudio
<!-- BEGIN PLATFORMS -->
_The release pipeline will populate per-platform downloads here on the first release._
<!-- END PLATFORMS -->


**Cross-Platform Design Suite with LLM Integration**

[![CI](https://github.com/embeddedos-org/EoStudio/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/embeddedos-org/EoStudio/actions)
[![CodeQL](https://github.com/embeddedos-org/EoStudio/actions/workflows/codeql.yml/badge.svg)](https://github.com/embeddedos-org/EoStudio/actions/workflows/codeql.yml)
[![Nightly](https://github.com/embeddedos-org/EoStudio/actions/workflows/nightly.yml/badge.svg)](https://github.com/embeddedos-org/EoStudio/actions/workflows/nightly.yml)
[![Release](https://github.com/embeddedos-org/EoStudio/actions/workflows/release.yml/badge.svg)](https://github.com/embeddedos-org/EoStudio/actions/workflows/release.yml)
[![Release Video](https://github.com/embeddedos-org/EoStudio/actions/workflows/release-video.yml/badge.svg)](https://github.com/embeddedos-org/EoStudio/actions/workflows/release-video.yml)
[![codecov](https://codecov.io/gh/embeddedos-org/EoStudio/branch/master/graph/badge.svg)](https://codecov.io/gh/embeddedos-org/EoStudio)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-1.0.0-blue)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Book](https://github.com/embeddedos-org/EoStudio/actions/workflows/book-build.yml/badge.svg)](https://github.com/embeddedos-org/EoStudio/actions/workflows/book-build.yml)

EoStudio is a unified design tool suite for the [EmbeddedOS](https://embeddedos-org.github.io) ecosystem — combining 3D modeling, CAD design, image editing, game design, UI/UX flow design, interior design, UML modeling, MATLAB-style simulation, multi-platform code generation, database design, LLM-powered AI assistance, **animation engine, interactive prototyping, video/promo generation, and React animation codegen** — all running on **Windows**, **Ubuntu/Linux**, and **EoS**.

## What's New in v1.0 (Community Edition)

- **Animation Engine** — Keyframe system with 25+ presets, spring physics, multi-track timeline widget
- **Design System** — Design tokens, light/dark themes, component variants with states, CSS/Tailwind/Style Dictionary export
- **Auto Layout** — Flexbox-like layout engine with responsive breakpoints (mobile → desktop)
- **AI UI Generation Pro** — Text-to-animated-UI, screenshot-to-UI, AI accessibility audit, color palette generation
- **Interactive Prototyping** — Interactions, gestures, screen transitions, state machine, HTML prototype export
- **Video & Promo** — Layer compositor, 6 promo templates (App Store, social media, product launch), MP4/GIF export
- **React Animation Codegen** — Generate full React apps with Framer Motion or GSAP animations from designs
- **Promo Editor** — Visual editor for creating promotional videos and social media content

## Quick Start

```bash
# Clone & install
git clone https://github.com/embeddedos-org/EoStudio.git
cd EoStudio
pip install -e ".[all]"

# Launch the design suite
EoStudio launch

# Create a project from template
EoStudio new --template todo-app -o ./my-app

# Generate React code from a design
EoStudio codegen my-app/todo-app.eostudio --framework react -o ./output

# Ask the AI design agent
EoStudio ask "Design a responsive dashboard with charts"

# Kids learning mode
EoStudio teach --lesson shapes
```

## Features

### 13 Design Editors

| Editor | CLI Flag | Use Case |
|--------|----------|----------|
| 3D Modeler | `--editor 3d` | Mesh modeling, materials, lighting |
| CAD Designer | `--editor cad` | Parametric design, assemblies, constraints |
| Image Editor | `--editor paint` | Layers, brushes, filters |
| Game Editor | `--editor game` | ECS, tilemaps, sprites |
| UI/UX Designer | `--editor ui` | Components, flows, prototyping, animation |
| Product Designer | `--editor product` | BOM, 3D-print validation |
| Interior Designer | `--editor interior` | Floor plans, furniture |
| UML Modeler | `--editor uml` | Class, sequence, state diagrams |
| Simulation Editor | `--editor simulation` | Block diagrams, PID, signals |
| Database Designer | `--editor database` | ERD, schema, SQL/ORM codegen |
| Hardware Editor | `--editor hardware` | PCB layout, schematics, Gerber |
| IDE | `--editor ide` | Code editing, debugging, Git |
| Promo Editor | `--editor promo` | Video promos, social media, App Store previews |

### 30+ Code Generators

| Target | Frameworks |
|--------|-----------|
| **Mobile** | Flutter, React Native, Kotlin (Android), Swift (iOS) |
| **Desktop** | Electron, Tauri, tkinter, Qt, Compose Desktop |
| **Web (Full-Stack)** | React+FastAPI, Vue+Flask, Angular+Express, Svelte+Django |
| **Web (Animated)** | React + Framer Motion, React + GSAP, React + CSS Animations |
| **Database** | SQLite, PostgreSQL, MySQL, SQLAlchemy, Prisma, Django Models |
| **UML → Code** | Python, Java, Kotlin, TypeScript, C++, C# |
| **3D/CAD** | OpenSCAD, STL, OBJ, glTF, DXF |
| **Game Engines** | Godot, Unity, Unreal |
| **Firmware** | EoS, Baremetal, FreeRTOS, Zephyr |

### AI & LLM Integration

| Feature | Description |
|---------|------------|
| **Design Agent** | Multi-domain Q&A, design brief generation, improvement suggestions |
| **Smart Chat** | Per-editor AI panel with context-aware prompts |
| **AI Generator** | Text-to-UI, text-to-3D, text-to-CAD design generation |
| **AI Generator Pro** | Text-to-animated-UI, screenshot-to-UI, AI design system generation |
| **AI Accessibility** | WCAG 2.1 AA audit with fix suggestions |
| **AI Palette** | Generate full color palette from a single brand color |
| **AI Simulator** | Parameter suggestion, instability detection, controller tuning |
| **Kids Tutor** | Interactive lessons with quizzes and encouragement |

### Animation & Motion

| Feature | Description |
|---------|------------|
| **Keyframe Engine** | Multi-track keyframes with 24 easing functions + cubic-bezier |
| **Spring Physics** | 6 spring presets (gentle, wobbly, stiff, etc.) like Framer Motion |
| **25 Presets** | fadeIn, slideUp, scaleIn, bounce, shake, pulse, revealUp, etc. |
| **Timeline Widget** | Visual keyframe editor with transport controls and scrubbing |
| **React Codegen** | Generate Framer Motion or GSAP animation code from designs |

### Prototyping

| Feature | Description |
|---------|------------|
| **Interactions** | 17 triggers (click, hover, scroll, gesture) × 18 actions |
| **Screen Transitions** | 15 types: fade, slide, push, scale, dissolve, shared element |
| **Gesture Recognition** | Swipe, pinch, long-press, tap with JS code generation |
| **State Machine** | Variables, conditions, guards for prototype logic |
| **HTML Export** | Share-able single-file interactive prototype |

### Video & Promo

| Feature | Description |
|---------|------------|
| **Promo Editor** | Visual layer compositor with real-time preview |
| **6 Templates** | App Store, social media (square/Twitter/LinkedIn), product launch, Product Hunt |
| **Export** | MP4, GIF, WebM via ffmpeg, 9 social media size presets |
| **Screen Recorder** | Record prototype sessions with annotations |

**LLM Backends:** Ollama (local, default) + OpenAI API — see [AI Guide](docs/ai-guide.md)

## AI / LLM Quick Setup

```bash
# Option 1: Ollama (local, private)
ollama pull llama3
EoStudio ask "Design a login page"

# Option 2: OpenAI API
export EOSTUDIO_LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-your-key
export EOSTUDIO_LLM_MODEL=gpt-4o
EoStudio ask --domain cad "Design an L-bracket with mounting holes"
```

## Example Projects

5 built-in templates demonstrating real workflows:

| Template | Workflow | Command |
|----------|----------|---------|
| `todo-app` | UI Designer → React/Flutter code | `EoStudio new --template todo-app -o ./app` |
| `mechanical-part` | CAD Designer → OpenSCAD → STL | `EoStudio new --template mechanical-part -o ./part` |
| `game-platformer` | Game Editor → Godot/Unity export | `EoStudio new --template game-platformer -o ./game` |
| `iot-dashboard` | Database + UI → Full-stack webapp | `EoStudio new --template iot-dashboard -o ./dash` |
| `simulation-pid` | Simulation Editor → PID analysis | `EoStudio new --template simulation-pid -o ./sim` |

## Documentation

| Guide | Description |
|-------|-------------|
| [Getting Started](docs/getting-started.md) | Installation, first project, basic usage |
| [Editors Guide](docs/editors-guide.md) | All 12 editors — features, components, shortcuts |
| [Code Generation Guide](docs/codegen-guide.md) | 30+ frameworks — usage, output structure |
| [AI & LLM Guide](docs/ai-guide.md) | LLM setup, Smart Chat, AI Generator, prompts |
| [Plugin Guide](docs/plugin-guide.md) | Plugin development — hooks, manifest, lifecycle |
| [Integration Guide](docs/integration-guide.md) | External tools, build systems, Git workflow |
| [Release Video Guide](docs/release-video-guide.md) | Automated release videos — CLI, CI/CD, Python API |
| [API Reference](docs/api-reference.md) | Python API for all modules |
| [Architecture](docs/architecture.md) | System design, module relationships, data flow |

## Architecture

```
eostudio/
├── cli/               # Click CLI (18 commands)
├── core/
│   ├── ai/            # LLMClient, DesignAgent, SmartChat, AIGenerator, AIGeneratorPro, Tutor
│   ├── animation/     # Keyframes, timeline, spring physics, 25 presets
│   ├── geometry/      # Vec2/3/4, Matrix4, Mesh, Bezier, NURBS, CSG
│   ├── rendering/     # Rasterizer, scene graph, camera, Phong lighting
│   ├── physics/       # Rigid body, collision, particles
│   ├── cad/           # Parametric design, constraints, assembly
│   ├── simulation/    # Block diagrams, PID, signals, ODE solver
│   ├── uml/           # 5 diagram types + code generation
│   ├── game/          # ECS, tilemap, sprites, scripting
│   ├── image/         # Layers, brushes, filters
│   ├── hardware/      # PCB, schematic, Gerber
│   ├── ui_flow/       # Design tokens, auto-layout, variants, responsive, design system
│   ├── interior/      # Floor plans, furniture
│   ├── prototyping/   # Interactions, transitions, gestures, state machine, player
│   └── video/         # Recorder, compositor, exporter, promo templates
├── gui/
│   ├── editors/       # 13 visual editors (including promo editor)
│   ├── widgets/       # Viewport, canvas, timeline, properties
│   └── dialogs/       # Export, settings, AI chat, design system
├── codegen/           # 30+ framework code generators + react_motion
├── formats/           # .EoStudio, OBJ, STL, SVG, glTF, DXF
├── plugins/           # Plugin system + EoSim integration
└── templates/         # 5 project templates
```

## Testing

```bash
# Install dev dependencies
pip install -e ".[dev,all]"

# Run all tests
pytest -v

# Run with coverage
pytest --cov=eostudio --cov-report=term-missing

# Lint
flake8 eostudio/ tests/ --max-line-length=120

# Type checking
mypy eostudio/ --ignore-missing-imports
```

**Test coverage:** 11 test files with 200+ test cases covering AI modules, geometry, codegen, plugins, simulation, formats, animation, design system, prototyping, video, react motion, and end-to-end integration.

## Plugin System

Extend EoStudio with custom tools, editors, and exporters:

```python
from eostudio.plugins.plugin_base import Plugin, PluginHook

class MyPlugin(Plugin):
    def activate(self, context):
        self._hooks[PluginHook.POST_CODEGEN] = self._on_codegen
        return super().activate(context)

    def _on_codegen(self, data):
        # Post-process generated code
        return {"processed": True}
```

See [Plugin Guide](docs/plugin-guide.md) for full documentation.

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Install dev dependencies: `pip install -e ".[dev,all]"`
4. Make your changes and add tests
5. Run tests: `pytest -v`
6. Submit a pull request

## Platform Support

| Platform | Status | Backend |
|----------|--------|---------|
| Windows 10/11 | ✅ | tkinter |
| Ubuntu 22.04+ | ✅ | tkinter |
| Linux (other) | ✅ | tkinter |
| macOS | ✅ | macOS native |
| EoS | ✅ | Framebuffer/SDL2 |
| Browser | 🔧 | Web backend |

## EoS Ecosystem

| Repo | Description |
|------|------------|
| [eos](https://github.com/embeddedos-org/eos) | Embedded OS — HAL, RTOS kernel, services |
| [eboot](https://github.com/embeddedos-org/eboot) | Bootloader — 24 board ports, secure boot |
| [ebuild](https://github.com/embeddedos-org/ebuild) | Build system — SDK generator, packaging |
| [eipc](https://github.com/embeddedos-org/eipc) | IPC framework — Go + C SDK, HMAC auth |
| [eai](https://github.com/embeddedos-org/eai) | AI layer — LLM inference, agent loop |
| [eApps](https://github.com/embeddedos-org/eApps) | Cross-platform apps — 38 C + LVGL apps |
| [eosim](https://github.com/embeddedos-org/eosim) | Multi-architecture simulator |
| **EoStudio** | **Design suite with LLM (this repo)** |

## License

MIT License — see [LICENSE](LICENSE) for details.

## Security

Please see [SECURITY.md](SECURITY.md) for reporting vulnerabilities.

