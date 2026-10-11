# Changelog

## [Unreleased]

### Fixed
- **EoStudio builds now go through ebuild's real CLI** (#24): new
  `eostudio/core/devtools/ebuild_backend.py` (`EbuildBackend`) translates the
  `EBUILD` `BuildConfig` into a real `ebuild` argv — `ebuild build`, `ebuild
  test`, `ebuild clean`, `ebuild monitor`, and `ebuild configure --board` for
  board selection — per ebuild's actual CLI contract, and
  `BuildSystemManager` routes ebuild-typed builds through it instead of
  shelling out command strings. Anything that cannot be translated, including
  previously emitted invalid invocations, now raises `EbuildBackendError`
  fail-closed instead of running a guessed command.

## [3.1.0] - 2026-05-27

### Added
- **Multi-Model AI Router (`multi_model_router.py`)**: Seamless orchestration across GPT-4.1, GPT-4.1-mini, GPT-4.1-nano, Gemini 2.5 Flash, Claude 3.5 Sonnet, and local Llama3 via Ollama. Features automatic model selection, cost tracking, latency monitoring, and automatic fallback chains.
- **AI Orchestrator (`orchestrator.py`)**: Multi-agent coordination (Planner, Executor, Reviewer, Tester, Debugger, Security, Documenter) with persistent, compressed long-term memory and Codebase RAG (Retrieval-Augmented Generation).
- **Self-Healing Code Engine**: Part of the AI Orchestrator, automatically compiles/tests code, captures errors, and iteratively fixes them via AI until successful execution.
- **Inline Code Completion (`inline_completion.py`)**: Cursor and GitHub Copilot-style ghost text completion engine. Context-aware (extracts imports, function signatures, and project context), features an LRU completion cache, and tracks acceptance rate telemetry.
- **Agentic Coder (`agentic_coder.py`)**: Devin and Claude Code-style autonomous task execution loop with plan-execute-test-fix cycle, shell tool integration, and automatic git commits.
- **Real-Time Collaboration (`realtime_collab.py`)**: Figma and CodeSandbox-style multi-user collaborative editing engine with Operational Transformation (OT) conflict resolution, user presence, active cursors, and revision history.
- **Workspace Intelligence (`workspace_intelligence.py`)**: Semantic codebase search, cross-file symbol indexing, architecture health scoring (0-100), dead code detection, circular dependency analysis, and auto-doc generation.
- **Voice-to-Code Interface (`voice_to_code.py`)**: Speech-to-code dictation, voice-driven editor actions (undo, save, run), design command interpreter, and AI voice query mode.
- **Live Preview Engine (`live_preview.py`)**: Multi-framework hot-reload preview (React, Next.js, Flutter, Flask, FastAPI, HTML) with file watching, error overlays, and AI-powered error fix suggestions.
- **Plugin Marketplace (`marketplace.py`)**: Built-in marketplace with one-click installation, dependency checking, auto-updates, and a curated catalog of 15+ plugins (AI, Themes, DevTools, Languages).
- **Smart Diff Viewer (`smart_diff.py`)**: Side-by-side and unified diff visualization with AI-generated explanations, security scanning (12 OWASP patterns), performance regression detection, and PR description auto-generation.
- **Security Hardening (`hardening.py`)**: Static Application Security Testing (SAST) with 12 built-in rules (SQL injection, command injection, path traversal, XSS, unsafe deserialization), secret/credential leak scanner, dependency vulnerability checker (pip-audit, npm audit), and HTML security report generator.
- **Interactive TUI Dashboard (`dashboard.py`)**: Beautiful terminal dashboard with project stats, git status, AI model health, keyboard shortcut cheatsheet, and command palette (Ctrl+P style) with fuzzy search.
- **Web Dashboard Server**: Local HTTP server serving a rich, responsive browser-based dashboard with real-time metrics and embedded AI Chat panel.
- **Enhanced CLI Commands**: Added `agent`, `complete`, `workspace`, `plugin`, `voice`, `query`, and `dashboard` to the `eostudio` CLI.
- **Comprehensive Unit Tests**: Added 53 new unit tests (`test_enhanced_features.py`) covering all new core modules with 100% pass rate.

### Changed
- Bumped version to `3.1.0` in `eostudio/__init__.py`.
- Upgraded the CLI entry point (`eostudio/cli/main.py`) to seamlessly register and expose all new commands.
- Enhanced the imports extraction pattern in `inline_completion.py` to extract precise module names for all supported languages.

---

## [3.0.1] - 2026-05-16

### Production Release — Unified EmbeddedOS-org v3.0.1

This is the synchronized production release across all 18 EmbeddedOS-org repos.

- Refreshed governance: LICENSE, NOTICE, CITATION.cff, SECURITY.md
- CI/CD pipelines hardened: release.yml, book-build.yml, video-build.yml, deploy-pages.yml
- Release artifacts produced for: Linux x64/arm64, macOS x64/arm64, Windows x64, Docker, plus per-repo embedded/mobile/extension targets
- mdBook documentation built and deployed to GitHub Pages
- Promo video rendered and attached as a release asset

## [3.0.0] - 2026-05-13

### Production Release — Unified EmbeddedOS-org v3.0.0

This is the synchronized production release across all 18 EmbeddedOS-org repos.

- Refreshed governance: LICENSE, NOTICE, CITATION.cff, SECURITY.md
- CI/CD pipelines hardened: release.yml, book-build.yml, video-build.yml, deploy-pages.yml
- Release artifacts produced for: Linux x64/arm64, macOS x64/arm64, Windows x64, Docker, plus per-repo embedded/mobile/extension targets
- mdBook documentation built and deployed to GitHub Pages
- Promo video rendered and attached as a release asset

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-04-28

### Added
- **Automated Release Video Pipeline** (`core/video/release_video.py`)
  - `ChangelogParser` — parses git history between version tags using conventional commits
  - `ReleaseVideoGenerator` — generates Manim scenes with 6 slides (hero, features, fixes, stats, breaking changes, CTA)
  - TTS narration via edge-tts with configurable voice, rate, and pitch
  - ffmpeg video+audio combine with duration capping
  - JSON manifest with version, duration, resolution, and changelog summary
  - Example output: `EoStudio release-video --version 2.0.0 --output ./release-artifacts/video`

- **CI/CD Pipeline Builder** (`core/devtools/cicd.py`)
  - `PipelineBuilder` with `add_release_video_step()` for automated video in CI
  - `create_release_with_video_pipeline()` — 4-stage template (Test → Build → Video → Publish)
  - `to_github_actions_yaml()` — generate GitHub Actions workflow YAML

- **GitHub Actions Workflow** (`.github/workflows/release-video.yml`)
  - Triggers on `v*` tags and manual dispatch
  - Installs ffmpeg, Manim, edge-tts; generates video; uploads as release asset
  - Inputs: version override, skip narration toggle

- **`release-video` CLI Command**
  - `EoStudio release-video` — generate release video from git changelog
  - Options: `--version`, `--output`, `--voice`, `--no-narration`, `--from-tag`, `--to-tag`, `--product-name`, `--tagline`

- **Documentation** (`docs/release-video-guide.md`)
  - CLI usage with examples, Python API reference, CI/CD integration (GitHub Actions, GitLab CI)
  - SVG slide mockups showing each video slide
  - Configuration reference, TTS voice table, troubleshooting

- **72 Integration Tests**
  - Changelog parsing with mock git output
  - Manim script generation and Python syntax validation
  - Narration script segment structure
  - E2E pipeline with realistic argument-aware subprocess mocks
  - CLI smoke tests using Click CliRunner

## [1.0.0] - 2026-04-25 — Community Edition

### Added
- **Animation Engine** (`core/animation/`)
  - Keyframe system with 24 easing functions + cubic-bezier support
  - AnimationTimeline with clips, sequencing, and stagger
  - Spring physics simulator with 6 presets (gentle, wobbly, stiff, slow, molasses)
  - 25 animation presets: fadeIn, slideUp, scaleIn, bounce, shake, pulse, revealUp, etc.
  - Visual timeline widget with keyframe editing, transport controls, and zoom

- **Design System** (`core/ui_flow/`)
  - Design tokens: colors, typography, spacing, shadows with light/dark themes
  - Auto-layout engine (flexbox-like with constraints)
  - Component variants with state overrides (hover, active, focus, disabled)
  - Responsive breakpoints (mobile_sm, mobile, tablet, desktop, desktop_lg)
  - Export to CSS variables, Tailwind config, Style Dictionary JSON

- **AI UI Generation Pro** (`core/ai/generator_pro.py`)
  - text_to_animated_ui: Generate UI + animation data from text prompt
  - text_to_design_system: Generate complete design system from brand description
  - screenshot_to_ui: Convert screenshot to component structure (vision LLM)
  - accessibility_audit: WCAG 2.1 AA compliance check with fix suggestions
  - generate_palette: Full color palette from single brand color
  - suggest_layout: AI-powered layout optimization

- **Interactive Prototyping** (`core/prototyping/`)
  - 17 interaction triggers × 18 action types with condition support
  - 15 screen transition types with Framer Motion props generation
  - Gesture recognition (swipe, pinch, long-press, tap) with JS code gen
  - Finite state machine for prototype logic with variables and guards
  - Prototype player with 8 device frames and HTML export

- **Video & Promo Generation** (`core/video/`)
  - Screen recorder with frame capture and annotations
  - Layer-based video compositor with keyframe animation
  - MP4/GIF/WebM export via ffmpeg with 9 social media size presets
  - 6 promo templates: App Store, social square, product launch, Twitter, LinkedIn, Product Hunt

- **React Animation Codegen** (`codegen/react_motion.py`)
  - Full React app generation with Framer Motion animations
  - Full React app generation with GSAP animations
  - CSS @keyframes fallback generation
  - useAnimation, useScrollAnimation, useParallax hooks
  - AnimatePresence page transitions, stagger containers

- **Promo Editor** (`gui/editors/promo_editor.py`)
  - Visual promo video editor with template browser
  - Real-time preview with scrubber and layer management
  - Export to MP4/GIF/WebM with preset sizes

- **Design System Dialog** (`gui/dialogs/design_system_dialog.py`)
  - Visual design system manager with color, typography, variant tabs
  - One-click export to CSS, Tailwind, Style Dictionary, JSON

- **8 New CLI Commands**
  - `EoStudio react-motion` — Generate animated React app
  - `EoStudio generate-ui` — AI text-to-animated-UI
  - `EoStudio design-system` — AI design system generation
  - `EoStudio screenshot-to-ui` — Screenshot to UI components
  - `EoStudio promo` — Generate promotional content
  - `EoStudio prototype` — Export interactive HTML prototype
  - `EoStudio palette` — Generate color palette from brand color
  - Updated `codegen` with react-framer-motion, react-gsap targets

- **Upgraded UI Designer** — Complete rewrite with 6 tabs:
  - Design canvas with responsive device frames
  - Flow view with screen management
  - Prototype tab with device preview and interactions
  - AI Generate tab with 5 generation modes
  - Bottom animation timeline widget
  - Component/Tokens/Animate left panels, Properties/Export/Responsive right panels

- **Comprehensive Tests** — 200+ test cases across 11 test files
  - Unit tests: animation, design system, prototyping, video, react motion
  - Integration tests: end-to-end design-to-code workflows

### Changed
- Editor count: 12 → 13 (added Promo Editor)
- EditorManager registry updated with `promo` editor
- App menus expanded: Animation, Prototype, Design System, Video & Promo
- `codegen/__init__.py` expanded with react-motion dispatchers

## [0.1.0] - 2026-03-31

### Added
- Initial release of EoStudio
- Complete CI/CD pipeline with nightly, weekly, and QEMU sanity runs
- Full cross-platform support (Linux, Windows, macOS)
- ISO/IEC standards compliance documentation
- MIT license

[2.0.0]: https://github.com/embeddedos-org/EoStudio/releases/tag/v2.0.0
[1.0.0]: https://github.com/embeddedos-org/EoStudio/releases/tag/v1.0.0
[0.1.0]: https://github.com/embeddedos-org/EoStudio/releases/tag/v0.1.0
