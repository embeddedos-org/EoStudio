# Repository Guidance for Agents

## Scope and architecture

EoStudio is a Python development and design platform for the EmbeddedOS
ecosystem. The `EoStudio` command-line entry point is implemented in
`eostudio/cli/`. Product logic is split across `eostudio/core/`, code generators
in `eostudio/codegen/`, import and export formats in `eostudio/formats/`, desktop
UI code in `eostudio/gui/`, platform adapters in `eostudio/platform/`, plugins in
`eostudio/plugins/`, and project templates in `eostudio/templates/`.

Follow the specialist role briefs in [`.ai/`](./.ai/) and the handoff protocol in
[`HANDOFF.md`](./HANDOFF.md). The implementer must not act as the approving
reviewer. Keep changes within the affected subsystem unless a shared interface
requires a coordinated update. EoStudio drives EmbeddedOS builds through
`ebuild`; do not duplicate ebuild's build orchestration inside this repository.

## Build and validation

Install development dependencies with `python -m pip install -e ".[dev]"`.
Use the narrowest pytest target that covers the change, then broaden validation
when shared behavior is affected.

- Run the full suite with `python -m pytest tests/ -v --tb=short`.
- Run static checks with `python -m ruff check eostudio/` and
  `python -m ruff format --check eostudio/`.
- Run typing checks with `python -m mypy eostudio/ --ignore-missing-imports`.
- For CLI changes, exercise the affected command through `EoStudio` or
  `python -m eostudio.cli.main` in addition to focused tests.
- For GUI, rendering, hardware, simulation, AI-provider, or external-service
  paths, record any SDK, display, device, credential, or network limitation
  instead of claiming unavailable integration coverage.

The CI matrix in [`.github/workflows/ci.yml`](./.github/workflows/ci.yml) covers
Python 3.10 through 3.12 on Linux, Windows, and macOS. A local run on one host
must not be described as matrix-wide validation.

## Change discipline

Preserve public CLI behavior, project and format compatibility, and optional
feature boundaries. Base installations must not acquire heavyweight AI,
database, cloud, or video dependencies unintentionally. Treat generated source,
format exports, plugin discovery, build command construction, remote URLs,
credentials, and file-system writes as security-sensitive boundaries.

Do not commit virtual environments, caches, build output, credentials, generated
media, or downloaded models unless the repository already tracks the exact
artifact and the change intentionally updates it. Update the relevant guides in
[`docs/`](./docs/), tests in [`tests/`](./tests/), and [`CHANGELOG.md`](./CHANGELOG.md)
when a user-facing contract changes.

Every human-authored pull request must use a GitHub-recognized closing keyword
for an issue in this repository, for example `Fixes #123`. Cross-repository
issues and plain issue mentions do not satisfy the linked-issue policy. Follow
[`.github/PULL_REQUEST_TEMPLATE.md`](./.github/PULL_REQUEST_TEMPLATE.md), and keep
the published Wiki snapshot in [`docs/wiki/`](./docs/wiki/) synchronized when
Wiki content changes.
