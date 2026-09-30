# CI and Phase Branch Workflow

## Branch Model

Use one branch per planned phase, based on the latest `main`:

| Phase | Branch |
|---|---|
| 0 — Repository Setup & CI/CD | `phase/0-repository-setup` |
| 1 — Voice Pipeline | `phase/1-voice-pipeline` |
| 2 — Intent Router & Screen Reading | `phase/2-intent-screen-reading` |
| 3 — Visual Overlay | `phase/3-visual-overlay` |
| 4 — AI Brain & Orchestrator | `phase/4-brain-orchestrator` |
| 5 — Memory System | `phase/5-memory-system` |
| 6 — Polish & Release | `phase/6-polish-release` |

Complete and merge each phase before branching the next. Use pull requests to merge into `main`; prefer squash merge so each phase lands as one reviewable commit. Do not work directly on `main`.

## What CI Runs

The workflows are `.github/workflows/ci.yml` and `.github/workflows/release.yml`. They use Windows runners with Python 3.12 and the committed `uv.lock`.

- **Every push to `phase/**`** runs `fast-checks`: Ruff lint/format, strict mypy, Bandit, and unit tests.
- **Pull requests targeting `main`** run `fast-checks` plus `merge-validation`: the full non-live/non-system test suite, `uv audit --locked`, and a PyInstaller smoke build.
- **Every push to `main` after a merge** reruns both jobs as post-merge verification.
- **Version tags matching `v*.*.*`** run the reusable full validation workflow, build `dist/krithika.exe`, then publish it as a GitHub Release asset.
- **Live API and interactive system tests** are excluded from hosted CI so no API secrets, microphone, or interactive desktop are exposed to PR code. Mark them `live_api` or `system`; run them locally with the phase-specific instructions.

The PR checks are what block a merge. The run after merge verifies the resulting `main`; it cannot prevent a merge that already happened. Required status checks in GitHub provide that gate.

Use `uv add <package>` for runtime dependencies and `uv add --group dev <package>` for developer tools. Commit the resulting `pyproject.toml` and `uv.lock` changes together; do not edit the lockfile manually. `uv sync --locked --all-groups` verifies and installs the committed resolution.

Dependabot monitors `uv.lock` through its dedicated `uv` ecosystem.

## GitHub Setup

1. Push the Phase 0 branch and open a PR to `main`. Confirm Actions is enabled under **Settings → Actions → General**. Keep the workflow token read-only; do not enable PR workflows to create or approve PRs.
2. Create a branch ruleset (or branch protection rule) targeting `main` under **Settings → Rules → Rulesets** (or **Settings → Branches**).
3. Require pull requests before merging. Require these checks after they appear in the PR check list: **`CI / fast-checks`** and **`CI / merge-validation`**. Require branches to be up to date and conversation resolution. Block force pushes and branch deletion.
4. Since this is a solo workflow, do not require an approval that you cannot provide yourself. If a second reviewer joins, require one approval and dismiss stale approvals.
5. Allow squash merging and enable linear history if desired. Do not enable a merge queue unless CI is also configured for GitHub's `merge_group` event.
6. If GitHub does not offer the check names before the initial CI PR is open, first add the ruleset with PR-only protection, open the PR and let checks run, then edit the ruleset to require both checks before merging that PR.

## Local Validation and Publishing

Before pushing, run the same checks locally:

```powershell
uv sync --locked --all-groups
uv lock --check
uv run ruff check .
uv run ruff format --check .
uv run mypy krithika
uv run bandit -r krithika -ll
uv run pytest tests -m "not live_api and not system" -v
uv audit --locked
scripts\build.bat
```

Push only after reviewing `git status` and staging intended files; avoid blindly staging local secrets or generated output. Then open a PR from the phase branch to `main`. GitHub Actions and required branch rules are repository-owner setup tasks.

After Phase 6 is ready for a release, create and push a version tag (for example, `v0.1.0`) from the approved `main` commit. The workflow validates the tag, builds the Windows executable, and publishes the release. The first real tag run is a manual acceptance check.

For a later phase, start from updated `main`:

```powershell
git switch main
git pull --ff-only
git switch -c phase/1-voice-pipeline
```
