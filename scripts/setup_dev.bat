@echo off
setlocal

where uv >nul 2>nul
if errorlevel 1 (
    echo uv is required. Install uv for Windows, then run this script again.
    exit /b 1
)

cd /d "%~dp0\.."
uv sync --locked --all-groups
if errorlevel 1 exit /b 1

uv run pre-commit install
if errorlevel 1 exit /b 1

echo Development environment is ready.
