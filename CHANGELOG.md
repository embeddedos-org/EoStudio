# Changelog

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
