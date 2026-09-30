# Phase 0 — Repository Setup & CI/CD

**Status:** In progress
**Date:** 2026-09-30

## Scope and Outcome

- Established the phase branch `phase/0-repository-setup`.
- Added baseline CI configuration; this is the initial infrastructure slice, not completion of all Phase 0 acceptance criteria.
- Added CI/branching instructions in `Implementation/CI_AND_BRANCHING.md`.
- Standardized dependency management on uv, replacing the temporary requirements-file approach.

## Design Decisions

- `pyproject.toml` owns runtime and development dependency declarations; `uv.lock` records their resolved versions.
- Phase branches run fast checks on every push.
- Pull requests to `main` and pushes to `main` additionally run the complete safe test suite and dependency audit.
- Live-API and interactive-system tests are excluded from hosted PR CI to avoid secrets and desktop/device dependencies.
- Use GitHub branch protection to require PR checks before merge; post-merge CI is verification, not a merge gate.

## Changed Files

- `.github/workflows/ci.yml` — Windows/Python 3.12 checks using `uv sync --locked --all-groups`, Ruff, mypy, Bandit, pytest, and `uv audit --locked`.
- `.github/dependabot.yml` — weekly updates for GitHub Actions and Python dependencies.
- `pyproject.toml` — project metadata, runtime/development dependency groups, uv version constraint, and shared tool configuration.
- `uv.lock` and `.python-version` — reproducible dependencies and Python 3.12 selection.
- `.gitignore` — ignores `.venv`, generated Python files, and local secrets/configuration.
- `Implementation/CI_AND_BRANCHING.md` — phase branch names, CI behavior, GitHub setup steps, and commands.
- `Plan/` — changed dependency guidance and commands across Phase 0–6 to use uv and `uv.lock`.

## Validation

| Check | Command or steps | Result |
|---|---|---|
| Branch | `git branch --show-current` | Passed: `phase/0-repository-setup` |
| Whitespace | Trailing-whitespace scan of new setup files | Passed |
| TOML config | Python `tomllib` parse of `pyproject.toml` | Passed |
| Lockfile | `uv lock --check` | Passed |
| Environment | `uv sync --locked --all-groups` | Passed: synchronized 36 packages in `.venv` |
| Lint | `uv run --no-sync ruff check .` | Passed |
| Formatting | `uv run --no-sync ruff format --check .` | Passed |
| Dependency audit | `uv audit --locked` | Passed: no known vulnerabilities found; uv reports the audit command as experimental |
| Workflow YAML parser | PyYAML parse of CI and Dependabot YAML | Passed |
| Mypy, Bandit, pytest | CI commands | Not run: application package and tests do not exist yet |
| GitHub Actions | Push branch and open PR | Pending |
| GitHub branch rules | Repository settings | Pending |

## Safety, Limitations, and Deviations

- No secrets are passed to pull-request workflows; live API and interactive Windows tests are excluded by marker.
- `uv audit` is currently marked experimental by the pinned uv release; keep its behavior under review as uv evolves.
- The workflow skips checks whose package/test directories do not exist yet. Those checks become active as Phase 0 scaffolding and later phases add code.
- Phase 0 remains incomplete until the workflow runs successfully on GitHub, required checks are configured on `main`, and the remaining Phase 0 checklist is addressed.

## Handoff

Push this branch, open a PR to `main`, verify the two CI jobs, and configure the `main` ruleset as documented in `Implementation/CI_AND_BRANCHING.md`. Then complete the remaining Phase 0 setup before branching Phase 1.

## Commit Recommendation

```text
Subject: build: standardize dependency management on uv

Body:
Use pyproject.toml and a committed uv.lock for runtime and development
dependencies. Run locked uv sync and checks in CI; update all phase plans
and setup guidance to use uv.

Validation: uv lock/sync/audit, Ruff lint/format, TOML, and YAML checks passed.
GitHub Actions checks are pending.
```
