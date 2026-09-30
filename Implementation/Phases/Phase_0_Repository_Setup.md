# Phase 0 — Repository Setup & CI/CD

**Status:** In progress — local implementation is ready for PR review; GitHub acceptance checks remain pending
**Updated:** 2026-09-30

## Delivered

- Created the repository-root `krithika/` package, module placeholders, unit/integration test folders, `prompts/`, and Windows setup/build scripts.
- Added typed Pydantic settings with YAML defaults and environment-variable overrides, including config lookup beside a packaged executable; added a minimal entry point, example configuration, and developer-facing README.
- Standardized dependency management on uv (`pyproject.toml`, pinned uv version, Python 3.12, and committed `uv.lock`); added Ruff, strict mypy, Bandit, pytest, pre-commit, and PyInstaller tooling.
- Added Windows CI for phase pushes, PRs, and `main`, with fast checks and stronger PR/main validation (safe full suite, dependency audit, executable smoke build).
- Added tag-triggered release automation that reuses full validation, builds `krithika.exe`, and creates a GitHub Release.
- Updated phase guidance and CI/branching documentation. The chosen repository-root package layout is intentional; the earlier “src layout” phrase was inconsistent with the rest of the planned tree.

## Design and Safety Decisions

- CI tests do not receive secrets and exclude `live_api` and `system` tests. GitHub branch rules, not a post-merge run, are the merge gate.
- Hosted dependencies are synchronized from the lockfile. GitHub Actions are pinned to reviewed commit SHAs.
- Phase 0 remains open until its PR checks pass, required `main` checks are configured, and a real release-tag run is exercised. Do not start Phase 1 before those gates are met or explicitly deferred.

## Validation Performed

| Check | Result |
|---|---|
| `uv sync --locked --all-groups`; `uv lock --check` | Passed |
| Ruff lint and format checks | Passed; 12 files already formatted |
| `uv run --no-sync mypy krithika` | Passed; 9 source files |
| `uv run --no-sync bandit -r krithika -ll` | Passed; no issues |
| Full safe pytest suite | Passed; 5 tests. This managed Windows environment denied pytest’s default system-temp path, so the suite passed with `-p no:cacheprovider --basetemp .pytest-tmp`. |
| `scripts/build.bat`; verify and run `dist\krithika.exe` | Passed; executable built, example config copied beside it, and packaged app launched |
| `uv audit --locked` | Passed; no known vulnerabilities in 43 packages (uv labels this command experimental) |
| CI/release/Dependabot YAML syntax | Passed with PyYAML |
| `git diff --check` | Passed |
| GitHub PR checks, `main` ruleset, tagged release workflow | Pending GitHub setup/real runs |

The first default pytest attempt hit environment filesystem restrictions, not an assertion failure. Re-running against a temporary directory inside the repository passed all tests. The executable smoke run confirms bootstrap packaging only; GUI/audio behavior is not implemented in this phase.

## Remaining Acceptance and Handoff

1. Push this branch and open the PR to `main`; confirm `CI / fast-checks` and `CI / merge-validation` succeed.
2. Configure the `main` ruleset to require both PR checks, then merge only after they pass.
3. Exercise `.github/workflows/release.yml` with a disposable `v0.0.1` tag when appropriate; document any GitHub-side limitations.

When those checks are complete, fill in the Phase 0 plan conclusion and mark the phase complete before creating the Phase 1 branch.
