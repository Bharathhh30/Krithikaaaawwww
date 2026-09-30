@echo off
setlocal

cd /d "%~dp0\.."
uv sync --locked --all-groups
if errorlevel 1 exit /b 1

uv run --no-sync pyinstaller --onefile --name krithika --windowed main.py
if errorlevel 1 exit /b 1

copy /y config.yaml.example dist\config.yaml.example >nul
if errorlevel 1 exit /b 1

echo Build complete: dist\krithika.exe and dist\config.yaml.example
