# Krithika

Krithika is a planned Windows 11 voice-operated AI companion that reads the
active screen and provides step-by-step visual guidance. This repository is
currently at **Phase 0**: project setup and CI are being established; voice and
screen features are not implemented yet.

## Requirements

- Windows 11
- Python 3.12
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

## Set up and run

```powershell
copy config.yaml.example config.yaml
# Add any needed API keys to your environment; never put secret values in config.yaml.
scripts\setup_dev.bat
uv run python main.py
```

`config.yaml` is local-only and ignored by Git. It stores provider choices and
the names of environment variables containing secrets—not the secret values.
The application currently validates configuration and logs that setup is ready.

## Development checks

```powershell
uv sync --locked --all-groups
uv run ruff check .
uv run ruff format --check .
uv run mypy krithika
uv run bandit -r krithika -ll
uv run pytest tests/unit -v
uv audit --locked
```

Add runtime packages with `uv add <package>` and development tools with
`uv add --group dev <package>`. Commit `pyproject.toml` and `uv.lock` together;
do not edit the lockfile manually.

Unit tests must not require a real microphone, third-party API, or desktop
interaction. Mark credential-dependent tests `live_api` and interactive
Windows/hardware tests `system`; hosted CI skips those markers.

## CI and phase workflow

Work on one `phase/<number>-<name>` branch at a time and merge through a PR to
`main`. Pushes to phase branches run fast checks. PRs to `main` run the safe
full suite and dependency audit as well. See
[`Implementation/CI_AND_BRANCHING.md`](Implementation/CI_AND_BRANCHING.md) for
branch protection steps and check names.

## Build

The Phase 0 bootstrap build is:

```powershell
scripts\build.bat
```

The build produces `dist\krithika.exe` and `dist\config.yaml.example`. For a
packaged build, copy the example to `config.yaml` beside the executable; the
application reads that adjacent file. Release tags publish both files.
