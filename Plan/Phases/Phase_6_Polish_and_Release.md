# Phase 6 — Polish, Voice & Release

## Overview

Make Krithika production-ready and distributable. This phase adds high-quality streaming TTS with a custom voice, robust error handling, "stop" voice commands, additional app-specific prompts, and packages everything into a single `.exe` that anyone can download and run. It also defines how to share Krithika with others.

---

## What We're Building

| Component | Purpose |
|---|---|
| ElevenLabs TTS (streaming) | High-quality voice with <300ms first-word latency |
| Custom voice setup | Configure the user's chosen voice via ElevenLabs |
| Error recovery | Graceful degradation on API failures, mic issues, timeout |
| Stop / cancel command | Voice command to interrupt Krithika mid-response |
| App-specific prompts | Expanded prompt library for common applications |
| PyInstaller packaging | Single `krithika.exe` — no Python required to run |
| GitHub Release | Automated release pipeline producing downloadable binary |
| First-run setup wizard | Console wizard for API keys on first launch |

---

## Files to Create / Modify

```
krithika/
└── tts/
    └── elevenlabs_tts.py   # Replace stub with full streaming implementation

krithika/
└── setup_wizard.py         # First-run console wizard for config

prompts/
├── photoshop.txt
├── vs_code.txt
├── excel.txt
├── chrome.txt
└── windows_explorer.txt

scripts/
└── build.bat               # Runs PyInstaller with correct flags

.github/workflows/
└── release.yml             # Updated: builds krithika.exe and uploads to GitHub Release

README.md                   # Updated: how to download, configure, and run

tests/unit/
└── test_elevenlabs_tts.py
```

---

## Implementation Details

### `elevenlabs_tts.py` — ElevenLabsTTSProvider (full implementation)

Replace the Phase 1 stub. Uses ElevenLabs streaming WebSocket:

```python
from elevenlabs.client import ElevenLabs
from elevenlabs import stream

class ElevenLabsTTSProvider(TTSProvider):
    def __init__(self, api_key: str, voice_id: str) -> None:
        self._client = ElevenLabs(api_key=api_key)
        self._voice_id = voice_id

    async def speak(self, text: str) -> None:
        """Stream audio — first chunk plays in ~300ms while rest generates."""
        audio_stream = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._client.generate(
                text=text,
                voice=self._voice_id,
                model="eleven_turbo_v2_5",
                stream=True,
            )
        )
        await asyncio.get_event_loop().run_in_executor(None, lambda: stream(audio_stream))
```

**Dual-layer TTS routing** (in `Orchestrator`):
- Short acknowledgments (< 8 words, "Got it", "Thinking...", "Looking at your screen") → `SAPITTSProvider` (instant)
- Full responses → `ElevenLabsTTSProvider` (streaming)

### Custom Voice Setup

Handled through `config.yaml`:
```yaml
tts:
  provider: elevenlabs
  api_key_env: ELEVENLABS_API_KEY
  voice_id: "abc123"    # ElevenLabs voice ID
```

To use voice cloning:
1. Record ~5 minutes of clean audio
2. Upload to ElevenLabs Voice Lab → get a `voice_id`
3. Paste `voice_id` into `config.yaml`

Document this process in `README.md` under "Custom Voice".

### `setup_wizard.py` — First-Run Wizard

Runs automatically the first time `main.py` is launched and `config.yaml` is missing or incomplete:

```
Welcome to Krithika Setup

Which AI provider do you want to use?
  [1] Anthropic Claude (recommended)
  [2] Google Gemini
  [3] OpenAI
  [4] Ollama (local, no API key needed)
Enter choice: _

Enter your Anthropic API key: _
Enter your TypeSafe API key: _
Enter your ElevenLabs API key (or press Enter to use Windows voice): _

Setup complete! Starting Krithika...
```

Writes a `config.yaml` from the user's answers. The wizard is console-based — no GUI dependency.

### Error Recovery (in `Orchestrator`)

Add a `try/except` wrapper around each stage of the loop with specific handlers:

| Error | Behaviour |
|---|---|
| `BrainUnavailableError` (API down) | Speak "I'm having trouble connecting. Please check your internet and try again." — continue loop |
| `TranscriptionError` | Speak "I didn't catch that — please say it again." — continue loop |
| `UIAReaderError` | Fall through to OmniParser silently |
| `ClickOutOfBoundsError` | Speak "I couldn't find that element on screen." — continue loop |
| Any unexpected exception | Log full traceback with `loguru`, speak "Something went wrong. I'm still listening." — continue loop |

The loop must **never crash**. A bad response from any API must not kill Krithika.

### Stop / Cancel Command

Already handled in Phase 2 as `IntentType.STOP`. In this phase, make stop interruptible mid-response:
- Start a background asyncio task for TTS
- When `STOP` is detected during speech, cancel the TTS task and immediately go back to listening state
- Speak a short acknowledgment using SAPI (instant): "Stopped."

### App-Specific Prompts

Each file in `prompts/` is loaded when the active application name matches (case-insensitive partial match):

```python
def load_app_prompt(active_app: str) -> str:
    for prompt_file in Path("prompts").glob("*.txt"):
        if prompt_file.stem.lower().replace("_", " ") in active_app.lower():
            return prompt_file.read_text()
    return ""
```

Each prompt file should include:
- Key panels and their names in that application
- Common tasks and which menus/buttons to use
- Any terminology specific to that app

### `scripts/build.bat` — PyInstaller Build

Add the build tool once during implementation, then commit the updated lockfile:

```powershell
uv add --group build pyinstaller
```

```bat
@echo off
uv sync --locked --all-groups
uv run --no-sync pyinstaller ^
  --onefile ^
  --name krithika ^
  --windowed ^
  --add-data "prompts;prompts" ^
  --add-data "config.yaml.example;." ^
  --add-data "models;models" ^
  --hidden-import "pywinauto" ^
  --hidden-import "pvporcupine" ^
  main.py
echo Build complete: dist\krithika.exe
```

`--windowed` suppresses the console window. Remove it during development/debugging.

### GitHub Actions — `release.yml` (updated)

Triggered by a tag push `v*.*.*`:

```yaml
jobs:
  ci:
    uses: ./.github/workflows/ci.yml
    with:
      full_validation: true

  build-windows:
    needs: ci
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v10.2.0
        with:
          version: "0.12.0"
          python-version: "3.12"
          enable-cache: true
      - run: uv sync --locked --all-groups
      - run: scripts\build.bat
      - name: Upload to GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          files: dist/krithika.exe
          generate_release_notes: true
```

---

## How to Share Krithika with Friends

### Option A — Share the `.exe` (easiest)

1. Push a git tag: `git tag v1.0.0 && git push origin v1.0.0`
2. GitHub Actions builds `krithika.exe` automatically
3. Download it from the GitHub Releases page
4. Share the download link

**Recipient setup** (no Python required):
1. Download `krithika.exe`
2. Run it — the setup wizard launches automatically on first run
3. Enter API keys when prompted
4. `krithika.exe` creates `config.yaml` next to itself

### Option B — Run from Source (for developers)

```bat
git clone https://github.com/yourusername/krithika.git
cd krithika
scripts\setup_dev.bat
copy config.yaml.example config.yaml
# Edit config.yaml — fill in API keys
python main.py
```

### Option C — Your own machine, daily use

Double-click `start.bat` at the repo root. Or add it to Windows Startup folder for auto-launch.

---

## Dependencies to Add with uv

```powershell
uv add "elevenlabs>=1.2.0"
```

Commit the resulting `pyproject.toml` and `uv.lock` changes together.

---

## Testing Requirements

### Unit Tests — `test_elevenlabs_tts.py`
- Mock the ElevenLabs SDK client and `stream` function
- Test that short text routes to SAPI, long text routes to ElevenLabs
- Test that API failure falls back to SAPI with an error log

### Manual Tests (required before release)
- [ ] Install `krithika.exe` on a clean Windows machine with no Python → it runs
- [ ] Setup wizard appears on first launch without `config.yaml`
- [ ] Custom voice plays correctly
- [ ] "Hey Krithika stop" interrupts mid-response
- [ ] All 5 app-specific prompts improve guidance quality vs no prompt

---

## Running Locally

```bat
scripts\build.bat
dist\krithika.exe
```

Test as if you are an end user — no `config.yaml` should exist when testing the wizard.

---

## Definition of Done

- `krithika.exe` runs on a clean Windows 11 machine without Python installed
- Setup wizard runs on first launch and creates a working `config.yaml`
- ElevenLabs TTS streams first audio within 300ms of response start
- "Hey Krithika stop" interrupts a TTS response within 500ms
- All error types in the error recovery table are handled without crashing
- GitHub Release contains a downloadable `krithika.exe` for the tag
- All unit tests pass in CI
- `README.md` has complete instructions for Option A, B, and C distribution

---

## Success Criteria

1. A friend with no Python experience can download `krithika.exe`, run the setup wizard, and be using Krithika within 5 minutes
2. ElevenLabs voice sounds natural and streams with no perceptible delay
3. Krithika survives 30 minutes of continuous use without crashing, even with deliberate bad inputs ("", very long sentences, rapid back-to-back questions)
4. App-specific prompts are demonstrably more helpful than the base prompt for supported apps

---

## Checklist

- [ ] `elevenlabs_tts.py` — full streaming implementation
- [ ] Dual-layer TTS routing (SAPI for short, ElevenLabs for full responses)
- [ ] Custom voice configured and tested
- [ ] `setup_wizard.py` — first-run console wizard
- [ ] Error recovery implemented for all 5 failure modes
- [ ] Stop-mid-response implemented
- [ ] `prompts/photoshop.txt`, `vs_code.txt`, `excel.txt`, `chrome.txt`, `windows_explorer.txt` written
- [ ] `scripts/build.bat` created and tested
- [ ] `release.yml` updated and tested with a tag
- [ ] `README.md` updated with distribution instructions
- [ ] Unit tests for ElevenLabs TTS
- [ ] Manual `.exe` test on clean machine
- [ ] CI pipeline passes
- [ ] v1.0.0 release on GitHub

---

## Conclusion

> *To be filled after completion.*
> Document voice quality, any PyInstaller packaging issues (missing DLLs, model files), distribution feedback from early users, and future improvement ideas.
