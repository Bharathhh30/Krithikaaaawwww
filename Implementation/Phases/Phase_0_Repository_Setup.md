# Phase 0 — Repository Setup & CI/CD

**Status:** Complete
**Completed:** 2026-09-30

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
| Phase 0 PR checks and post-merge CI | Passed (confirmed by repository owner) |
| Release workflow on `v0.0.1` | Passed; run `36721293529` completed successfully |
| GitHub Release assets | Uploaded: `krithika.exe` (17,465,829 bytes) and `config.yaml.example` (336 bytes) |

The first default pytest attempt hit environment filesystem restrictions, not an assertion failure. Re-running against a temporary directory inside the repository passed all tests. The executable smoke run confirms bootstrap packaging only; GUI/audio behavior is not implemented in this phase.

## Completion and Handoff

The Phase 0 PR checks and post-merge CI passed. The `v0.0.1` tag triggered the release workflow; validation, packaging, and GitHub Release publication all succeeded with both expected assets. The `main` branch ruleset was configured as part of the merge process.

Begin Phase 1 from the latest `main` on `phase/1-voice-pipeline`. The release workflow test created a real `v0.0.1` GitHub Release; treat that as an infrastructure test release, not a user-facing product release.
