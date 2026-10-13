---
name: eostudio-ebuild
description: Build, test, clean, run, and configure EmbeddedOS projects through EoStudio's ebuild route — the project's BuildConfig translated to a real ebuild argv by EbuildBackend. Use when an agent needs to build a project that EoStudio manages, interpret an ebuild result from inside EoStudio, or drive the configure → build → run lifecycle without inventing its own compile commands.
---

# EoStudio ebuild Build Route

Build EoStudio projects the one supported way: the project's
`BuildConfig` goes to `EbuildBackend`
(`eostudio/core/devtools/ebuild_backend.py`), which translates it
into a real `ebuild` argv and executes it — no shell, no ad-hoc
compiler invocations. This skill is the agent-facing contract for
that route.

## Quick start

```python
from eostudio.core.devtools.build_system import BuildConfig
from eostudio.core.devtools.ebuild_backend import EbuildBackend

backend = EbuildBackend(workspace="path/to/project")

backend.configure("rp2350")                      # ebuild configure --board rp2350
result = backend.build(BuildConfig(...))         # ebuild build …
result = backend.test(BuildConfig(...))          # ebuild test …
result = backend.run(BuildConfig(...))           # ebuild monitor … (the "run" action)
backend.clean(BuildConfig(...))                  # ebuild clean …
```

Dry-run any route first by asking the backend for the argv instead
of executing it: `build_argv(config, board=…)`, `test_argv(config)`,
`clean_argv(config)`, `run_argv(config)`, `configure_argv(board)`.

## What it answers

- **"Build this project"** — `configure` (board stays explicit) then
  `build`, reporting the `BuildResult`, not a paraphrase of it.
- **"Did it pass?"** — interpret the result the backend already
  computed: `BuildResult.success` is exactly `returncode == 0`, and
  `errors` is populated on non-zero exits. Exit code 0 is the only
  success; a build that "mostly worked" is a failed build.
- **"Run it on the board"** — `run` is the monitor route
  (`ebuild monitor`); port and baud come from the config, never from
  flags the agent invents.
- **"What would it run?"** — the `*_argv` builders above are pure;
  show the argv before executing anything consequential.

## Discipline

1. **Fail closed on the config.** If the `BuildConfig` is not an
   ebuild config, `EbuildBackend` raises `EbuildBackendError` —
   it refuses to translate another build system's commands into
   ebuild argv. An invalid or foreign config stops the workflow;
   report the error, do not work around it.
2. **Never fall back to ad-hoc compile commands.** No direct
   `gcc`/`cmake`/`ninja` invocations when this route fails. A failed
   ebuild route is a failed build with a report, not an invitation
   to improvise one.
3. **No shell.** The backend executes an argv list directly so
   nothing can be smuggled in through a command string; keep it that
   way — never re-join argv into a shell line.
4. **Board selection stays explicit.** `configure` and `build` name
   the board; a missing board is an error to surface, not a default
   to guess.
