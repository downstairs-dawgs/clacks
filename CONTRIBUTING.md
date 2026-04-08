# Contributing to clacks

## Setup

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/downstairs-dawgs/clacks.git
cd clacks
uv sync --group dev
```

## Checks

Before opening a PR, run all checks:

```bash
uv run ruff check          # lint
uv run ruff format --check # format check
uv run mypy src/           # typecheck
uv run python -m unittest discover -s tests  # tests
```

To auto-fix lint and formatting issues:

```bash
uv run ruff check --fix
uv run ruff format
```

## Version bumps

Every PR must bump the version in `pyproject.toml` unless the PR **only** touches
documentation -- top-level `.md` files, the `docs/` directory, or `.github/`. If your
change touches any code, tests, or configuration, bump the version.

The version is the `version` field in the `[project]` section of `pyproject.toml`.

## Pull requests

- Branch from `main`.
- Keep PRs focused -- one logical change per PR.
- Make sure all checks pass before requesting review.
