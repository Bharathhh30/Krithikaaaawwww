# Phase 0 — Repository Setup & CI/CD

## Overview

Before any feature code is written, the repository must be production-grade from day one. This phase establishes the project structure, development tooling, CI/CD pipeline, configuration management, and the baseline for how every subsequent phase is built and tested.

---

## What We're Building

- Python package structure following the `src` layout pattern
- Configuration management with Pydantic BaseSettings and `config.yaml`
- GitHub Actions CI pipeline (lint + type-check + test on every push/PR)
- GitHub Actions release pipeline (build `.exe` on git tag)
- Pre-commit hooks for local enforcement
- Test scaffolding with pytest
- Developer setup script for Windows (`scripts/setup_dev.bat`)
- User launch script (`start.bat` at repo root)

---

## Repository Structure to Create

```
krithika/                          ← repo root
├── .github/
│   └── workflows/
│       ├── ci.yml                 ← runs on every push / PR
│       └── release.yml            ← runs on git tag v*.*.*
├── krithika/                      ← main Python package
│   ├── __init__.py
│   ├── voice/
│   ├── intent/
│   ├── screen/
│   ├── brain/
│   ├── overlay/
│   ├── tts/
│   ├── memory/
│   ├── clicker.py
│   └── orchestrator.py
├── tests/
│   ├── unit/
│   └── integration/
├── prompts/                       ← system prompt text files
├── scripts/
│   └── setup_dev.bat              ← installs deps + pre-commit hooks
├── config.yaml.example            ← committed template, never config.yaml
├── main.py                        ← entry point: python main.py
├── start.bat                      ← double-click to launch on Windows
├── pyproject.toml                 ← ruff, mypy, pytest config
├── requirements.txt               ← runtime dependencies
├── requirements-dev.txt           ← dev-only: pytest, ruff, mypy, bandit
├── .pre-commit-config.yaml
├── .gitignore
└── README.md
```

---

## Implementation Details

### `pyproject.toml`

Configure all tooling in one file:

```toml
[tool.ruff]
line-length = 100
select = ["E", "F", "W", "I", "UP", "B"]

[tool.mypy]
python_version = "3.12"
strict = true
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
markers = ["integration: marks tests as integration tests (deselect with -m 'not integration')"]
```

### `config.yaml.example`

```yaml
brain:
  provider: claude              # claude | gemini | openai | ollama
  model: claude-sonnet-5
  api_key_env: ANTHROPIC_API_KEY

classifier:
  api_key_env: TYPESAFE_API_KEY

tts:
  provider: elevenlabs          # elevenlabs | sapi
  api_key_env: ELEVENLABS_API_KEY
  voice_id: ""                  # fill in Phase 6

wake_word:
  keyword: krithika
  access_key_env: PORCUPINE_ACCESS_KEY

memory:
  vault_path: ""                # leave blank to use ~/KrithikaMemory

log_level: INFO
```

Load with Pydantic BaseSettings so every missing required key raises a clear error at startup, not mid-run.

### `config.yaml` is in `.gitignore`

Never commit real API keys. The example file is committed; the user copies it:
```
copy config.yaml.example config.yaml
```

### `start.bat`

```bat
@echo off
python main.py
pause
```

Double-click to run Krithika. The `pause` keeps the window open if it crashes so the user can read the error.

### `.github/workflows/ci.yml`

Triggers: push and pull_request to `main` and `develop`.

Steps in order:
1. Checkout
2. Set up Python 3.12
3. Install `requirements-dev.txt`
4. **Ruff lint** — `ruff check .`
5. **Mypy type check** — `mypy krithika/`
6. **Bandit security scan** — `bandit -r krithika/ -ll` (medium severity and above fails the build)
7. **Unit tests** — `pytest tests/unit/ -v`
8. **Integration tests** — `pytest tests/integration/ -v -m integration` (may be skipped in CI if they need live APIs — use `@pytest.mark.integration` and a `RUN_INTEGRATION=true` env gate)

### `.github/workflows/release.yml`

Triggers: push of tag matching `v*.*.*`.

Steps:
1. All CI steps above must pass first (use `needs: ci`)
2. Install PyInstaller
3. `pyinstaller --onefile --name krithika --windowed main.py`
4. Upload `dist/krithika.exe` as a GitHub Release asset

### `scripts/setup_dev.bat`

```bat
@echo off
pip install -r requirements.txt
pip install -r requirements-dev.txt
pre-commit install
echo Setup complete.
```

---

## Coding Standards (Applies to All Phases)

These are enforced by tooling — not guidelines, hard rules:

- **Type hints on every function signature** — mypy strict mode will fail the build otherwise
- **SOLID principles**:
  - *Single Responsibility*: one class per file where possible; no "god" modules
  - *Open/Closed*: extend via new adapter/subclass, never modify existing ones
  - *Liskov Substitution*: all `BrainAdapter` implementations must be swappable
  - *Interface Segregation*: small, focused ABCs — not one giant interface
  - *Dependency Inversion*: high-level modules (orchestrator) depend on abstractions (BrainAdapter), not concretions (ClaudeAdapter)
- **Async all the way down**: the entire pipeline is `asyncio`. No `time.sleep`, no blocking I/O in the main loop
- **Structured logging** with `loguru` — not `print()`. Every module gets `from loguru import logger`
- **Dataclasses or Pydantic models** for all data that crosses module boundaries — no raw dicts
- **No bare `except`** — always catch specific exceptions

---

## Running Locally

```bat
# First time setup
copy config.yaml.example config.yaml
# Edit config.yaml — fill in API keys

scripts\setup_dev.bat

# Run
python main.py
```

---

## Definition of Done

- Repo structure matches the layout above exactly
- `python main.py` starts without error (even if it exits immediately — no code yet)
- `ruff check .` passes with zero warnings
- `mypy krithika/` passes
- `pytest tests/` passes (zero tests = zero failures is fine for this phase)
- CI pipeline runs green on a push to `main`
- `config.yaml.example` has all keys documented
- `README.md` has setup and run instructions

---

## Success Criteria

1. A new developer (or coding agent) can clone the repo, run `scripts/setup_dev.bat`, copy `config.yaml.example`, and be ready to develop in under 5 minutes
2. A bad import or type error in any `krithika/` file fails the CI pipeline automatically
3. Pushing a `v0.1.0` tag produces a downloadable `krithika.exe` in GitHub Releases

---

## Checklist

- [ ] Repo folder structure created as specified
- [ ] `pyproject.toml` configured (ruff, mypy, pytest)
- [ ] `requirements.txt` created (empty or placeholder)
- [ ] `requirements-dev.txt` created (ruff, mypy, pytest, pytest-asyncio, bandit, pre-commit, loguru)
- [ ] `config.yaml.example` created with all keys
- [ ] `config.yaml` added to `.gitignore`
- [ ] `.pre-commit-config.yaml` configured (ruff, mypy)
- [ ] `main.py` created (minimal — just imports and a `if __name__ == "__main__"` block)
- [ ] `start.bat` created
- [ ] `scripts/setup_dev.bat` created
- [ ] `.github/workflows/ci.yml` created and tested
- [ ] `.github/workflows/release.yml` created
- [ ] `README.md` created with setup + run instructions
- [ ] CI pipeline passes on push to `main`
- [ ] Release pipeline tested with a `v0.0.1` tag

---

## Conclusion

> *To be filled after completion.*
> Document what was built, any deviations from the plan, decisions made during implementation, and anything the next phase needs to know.
