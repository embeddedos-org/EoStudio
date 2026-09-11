# Development

## Contribution source of truth

[CONTRIBUTING](https://github.com/embeddedos-org/EoStudio/blob/master/CONTRIBUTING.md)

Before proposing a change, also review the [README](https://github.com/embeddedos-org/EoStudio/blob/master/README.md). Keep changes scoped, add tests appropriate to the affected behavior, and follow the repository's current automation and review requirements.

## Build and dependency inputs found

`Dockerfile`, `docker-compose.yml`, `enterprise/docker/Dockerfile`, `enterprise/docker/docker-compose.yml`, `pyproject.toml`.

## Tests found in the default-branch tree

`eostudio/core/specs/__init__.py`, `eostudio/core/specs/design_spec.py`, `eostudio/core/specs/requirement.py`, `eostudio/core/specs/spec_engine.py`, `eostudio/core/specs/task_breakdown.py`, `eostudio/core/specs/tech_spec.py`, `tests/__init__.py`, `tests/functional/test_functional_e2e.py`, `tests/integration/__init__.py`, `tests/integration/test_e2e_workflow.py`, `tests/integration/test_project.py`, `tests/integration/test_release_video.py`, and 20 more.

## Documented test commands

These commands are reproduced from the inspected root README or contributing guide:

```bash
pytest        # tests/ (configured in pyproject.toml)
```

```bash
python3 -m pytest tests/ -v
```

## Verification baseline

This inventory comes from `master` at [`2711efe4b98c`](https://github.com/embeddedos-org/EoStudio/commit/2711efe4b98ca787f7670466ff47216ba4d55630) and found 32 test-related paths among 947 files. Re-check the source tree when that commit is no longer current.
