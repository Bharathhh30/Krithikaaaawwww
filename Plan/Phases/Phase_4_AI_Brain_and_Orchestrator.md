# Phase 4 — AI Brain, Adapter Pattern & Orchestrator

## Overview

Wire everything together. This phase builds the provider-agnostic AI Brain using the adapter pattern, the click executor, and the main async orchestrator loop that connects voice → intent → screen → brain → overlay + TTS in a single continuous pipeline. After this phase, Krithika is fully functional end-to-end.

---

## What We're Building

| Component | Purpose |
|---|---|
| `BrainAdapter` ABC | Abstract interface all AI providers implement |
| `ClaudeAdapter` | Default brain using Anthropic claude-sonnet-5 with vision |
| `OllamaAdapter` | Local fallback brain using Ollama (LLaVA or similar) |
| `GeminiAdapter` | Stub for Google Gemini (fully implemented if user has key) |
| `OpenAIAdapter` | Stub for OpenAI GPT-4o |
| `ActionExecutor` | Executes any computer action on command — click, type, key press, open app, hotkey, sequences |
| `Orchestrator` | Main asyncio loop connecting all components |
| Config loader | Pydantic BaseSettings loading `config.yaml` |

---

## Files to Create

```
krithika/
└── brain/
    ├── __init__.py
    ├── adapter.py          # BrainAdapter ABC + BrainContext + BrainResponse
    ├── claude_adapter.py   # ClaudeAdapter (default)
    ├── ollama_adapter.py   # OllamaAdapter (local fallback)
    ├── gemini_adapter.py   # GeminiAdapter (stub or full)
    ├── openai_adapter.py   # OpenAIAdapter (stub or full)
    └── factory.py          # create_brain_adapter(config) factory function

krithika/
├── action_executor.py      # ActionExecutor — click, type, key, open app, hotkey, sequences
├── orchestrator.py         # Main async loop
└── config.py               # Pydantic BaseSettings config loader

prompts/
├── system_base.txt         # Base Krithika personality
├── davinci_resolve.txt     # App-specific prompt injection
├── photoshop.txt
└── windows_settings.txt

tests/unit/
├── test_claude_adapter.py
├── test_orchestrator.py
└── test_action_executor.py

tests/integration/
└── test_full_pipeline.py
```

---

## Implementation Details

### `adapter.py` — BrainAdapter ABC

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

@dataclass
class BrainContext:
    user_query: str
    screenshot: bytes | None
    ui_elements: list[UIElement]
    working_memory: dict
    retrieved_memory: str
    active_app: str

@dataclass
class HighlightSpec:
    element_name: str
    x: int
    y: int
    width: int
    height: int
    animation: str = "pulse"

@dataclass
class BrainResponse:
    speak: str
    highlight: HighlightSpec | None = None
    click_target: str | None = None       # element name — only set if user said "click X"
    next_step: str | None = None
    memory_write: dict | None = None

class BrainAdapter(ABC):
    @abstractmethod
    async def process(self, context: BrainContext) -> BrainResponse:
        """Process the context and return guidance. Must be non-blocking (run heavy work in thread pool)."""
```

### `claude_adapter.py` — ClaudeAdapter

- Uses `anthropic` Python SDK with `client.messages.create(..., stream=True)`
- System prompt assembled from `prompts/system_base.txt` + app-specific prompt if file exists for `active_app`
- Screenshot (if provided) sent as `image/jpeg` base64 content block
- UI elements list sent as JSON in the user message
- Response parsed from streaming output into `BrainResponse`
- Model: `claude-sonnet-5` (configurable via `config.yaml`)

**Prompt injection** — system prompt structure:
```
{system_base.txt content}

Active application: {active_app}
{app_specific_prompt if exists}

Current task: {working_memory.current_task}
Step: {working_memory.step} of {working_memory.total_steps}
Relevant memory: {retrieved_memory}
Available UI elements: {json.dumps(ui_elements)}
```

**Structured output**: Instruct Claude to respond in JSON matching `BrainResponse`. Use a JSON block at the end of the response separated by `---JSON---` to allow natural language streaming before the structured part.

### `ollama_adapter.py` — OllamaAdapter

- Uses `ollama` Python library
- Model: `llava` or `llava-next` (vision-capable)
- Same interface as `ClaudeAdapter` — fully swappable
- Falls back gracefully if Ollama is not running (raises `BrainUnavailableError`)

### `gemini_adapter.py` and `openai_adapter.py`

If the user does not have the respective API key configured, these raise `BrainUnavailableError` with a clear message. If the key is present, they implement the full adapter. Structure mirrors `ClaudeAdapter`.

### `factory.py` — create_brain_adapter

```python
def create_brain_adapter(config: KrithikaConfig) -> BrainAdapter:
    """Return the correct adapter based on config.brain.provider."""
    match config.brain.provider:
        case "claude":  return ClaudeAdapter(config)
        case "ollama":  return OllamaAdapter(config)
        case "gemini":  return GeminiAdapter(config)
        case "openai":  return OpenAIAdapter(config)
        case _:         raise ValueError(f"Unknown provider: {config.brain.provider}")
```

### `action_executor.py` — ActionExecutor

Handles all computer actions triggered by voice command. Every action is **immediate** — the user's voice is the confirmation.

```python
from enum import Enum
from dataclasses import dataclass, field
import pyautogui
import subprocess
import pywin32

class ActionType(str, Enum):
    CLICK        = "click"          # click a UIElement
    TYPE_TEXT    = "type_text"      # type a string into the focused field
    PRESS_KEY    = "press_key"      # press a single key ("enter", "tab", "escape", etc.)
    HOTKEY       = "hotkey"         # keyboard shortcut (["ctrl", "c"], ["win", "r"])
    OPEN_APP     = "open_app"       # launch an application by name
    FOCUS_WINDOW = "focus_window"   # bring a window to the foreground
    SCROLL       = "scroll"         # scroll up or down
    SEQUENCE     = "sequence"       # ordered list of the above actions

@dataclass
class ActionSpec:
    action_type: ActionType
    # CLICK
    element: UIElement | None = None
    # TYPE_TEXT
    text: str | None = None
    # PRESS_KEY
    key: str | None = None
    # HOTKEY
    keys: list[str] = field(default_factory=list)
    # OPEN_APP
    app_name: str | None = None
    # FOCUS_WINDOW
    window_title: str | None = None
    # SCROLL
    direction: str | None = None     # "up" | "down"
    amount: int = 3                  # scroll clicks
    # SEQUENCE
    steps: list["ActionSpec"] = field(default_factory=list)
    # Optional wait after this action (milliseconds)
    wait_after_ms: int = 0

class ActionExecutor:
    def __init__(self) -> None:
        pyautogui.FAILSAFE = True    # move mouse to top-left to abort

    def execute(self, spec: ActionSpec) -> None:
        """Execute an action spec. For SEQUENCE, runs each step in order."""
        match spec.action_type:
            case ActionType.CLICK:
                self._click(spec)
            case ActionType.TYPE_TEXT:
                pyautogui.write(spec.text, interval=0.03)
            case ActionType.PRESS_KEY:
                pyautogui.press(spec.key)
            case ActionType.HOTKEY:
                pyautogui.hotkey(*spec.keys)
            case ActionType.OPEN_APP:
                self._open_app(spec.app_name)
            case ActionType.FOCUS_WINDOW:
                self._focus_window(spec.window_title)
            case ActionType.SCROLL:
                clicks = spec.amount if spec.direction == "up" else -spec.amount
                pyautogui.scroll(clicks)
            case ActionType.SEQUENCE:
                for step in spec.steps:
                    self.execute(step)
                    if step.wait_after_ms:
                        import time; time.sleep(step.wait_after_ms / 1000)

    def _click(self, spec: ActionSpec) -> None:
        if spec.element is None:
            raise ValueError("CLICK action requires an element")
        cx, cy = spec.element.center
        if not self._in_bounds(cx, cy):
            raise ClickOutOfBoundsError(f"Coordinates ({cx}, {cy}) are off-screen")
        pyautogui.click(cx, cy)

    def _open_app(self, app_name: str) -> None:
        """Launch app by name. Tries common Windows paths and the shell."""
        subprocess.Popen(["start", app_name], shell=True)

    def _focus_window(self, title: str) -> None:
        """Bring the first window whose title contains `title` to the foreground."""
        import win32gui, win32con
        hwnd = win32gui.FindWindow(None, title) or self._find_partial(title)
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
```

**How `ACTION_COMMAND` flows through the system**:

1. Jev classifies voice command as `ACTION_COMMAND`
2. Orchestrator passes the full command to the AI Brain (no screenshot needed for most actions)
3. Brain returns `BrainResponse.action: ActionSpec` describing the exact steps
4. Orchestrator calls `ActionExecutor.execute(spec)` — immediate
5. TTS confirms: "Done" or describes what happened

**Example — "open terminal, type claude, press enter"**:

Brain returns:
```json
{
  "speak": "Opening terminal and starting Claude Code",
  "action": {
    "action_type": "sequence",
    "steps": [
      {"action_type": "open_app", "app_name": "wt", "wait_after_ms": 1500},
      {"action_type": "type_text", "text": "claude"},
      {"action_type": "press_key", "key": "enter"}
    ]
  }
}
```

**More examples**:

| Voice command | ActionSpec produced |
|---|---|
| "Open Notepad" | `OPEN_APP, app_name="notepad"` |
| "Type hello world" | `TYPE_TEXT, text="hello world"` |
| "Press Enter" | `PRESS_KEY, key="enter"` |
| "Press Control C" | `HOTKEY, keys=["ctrl","c"]` |
| "Scroll down" | `SCROLL, direction="down", amount=3` |
| "Switch to Chrome" | `FOCUS_WINDOW, window_title="Chrome"` |
| "Open terminal and run git status" | `SEQUENCE: OPEN_APP → wait → TYPE_TEXT("git status") → PRESS_KEY("enter")` |

**`BrainResponse` updated** to include the action field:

```python
@dataclass
class BrainResponse:
    speak: str
    highlight: HighlightSpec | None = None
    click_target: str | None = None    # for CLICK_COMMAND (uses UIElement, not ActionSpec)
    action: ActionSpec | None = None   # for ACTION_COMMAND
    next_step: str | None = None
    memory_write: dict | None = None
```

### `config.py` — KrithikaConfig

```python
from pydantic_settings import BaseSettings
import yaml

class KrithikaConfig(BaseSettings):
    brain_provider: str = "claude"
    brain_model: str = "claude-sonnet-5"
    # ... all config keys with defaults

    @classmethod
    def from_yaml(cls, path: str = "config.yaml") -> "KrithikaConfig":
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)
```

Raises a clear `ConfigurationError` (not a generic exception) if a required API key env variable is missing.

### `orchestrator.py` — Orchestrator

The main asyncio loop. Dependency-injected — it receives all components through `__init__`, never instantiates them itself (Dependency Inversion Principle).

```python
class Orchestrator:
    def __init__(
        self,
        wake_word: WakeWordDetector,
        recorder: AudioRecorder,
        transcriber: WhisperTranscriber,
        router: IntentRouter,
        uia_reader: UIAReader,
        screen_capture: ScreenCapture,
        omniparser: OmniParserReader,
        element_selector: ElementSelector,
        brain: BrainAdapter,
        overlay: OverlayApp,
        tts: TTSProvider,
        memory: MemoryManager,   # Phase 5 — inject a stub in this phase
        clicker: Clicker,
    ) -> None: ...

    async def run(self) -> None:
        """Main loop. Runs indefinitely until STOP intent or KeyboardInterrupt."""
```

**Loop flow**:
```
wake_word.wait_for_wake_word()
  → overlay.set_hud_state("listening")
  → recorder.record_until_silence()  [parallel with initial screenshot]
  → transcriber.transcribe(audio)
  → overlay.set_hud_state("thinking")
  → router.classify(text, active_app, working_memory)
  → [if STOP] handle_stop()
  → [if needs_screen] uia_reader.get_elements() → element_selector or fallback
  → [if CLICK_COMMAND] clicker.click(element) + speak + continue
  → memory.retrieve(text, active_app)  [Phase 5 stub returns "" for now]
  → brain.process(BrainContext(...))
  → asyncio.gather(tts.speak(response.speak), overlay.highlight(response.highlight))
  → memory.write(...)  [Phase 5 stub is a no-op for now]
```

### `main.py` — Entry Point

```python
def main() -> None:
    config = KrithikaConfig.from_yaml()
    # Instantiate all components
    # Inject into Orchestrator
    # Run asyncio.run(orchestrator.run())

if __name__ == "__main__":
    main()
```

---

## Dependencies to Add to `requirements.txt`

```
anthropic>=0.28.0
ollama>=0.2.0
pyautogui>=0.9.54
pydantic-settings>=2.0.0
pyyaml>=6.0.1
```

---

## Testing Requirements

### Unit Tests — `test_claude_adapter.py`
- Mock the `anthropic` SDK client
- Test that `BrainContext` is serialised correctly into the API call
- Test that a well-formed mock response is parsed into a correct `BrainResponse`
- Test that app-specific prompts are injected when the file exists

### Unit Tests — `test_orchestrator.py`
- Mock all injected components
- Test the full loop for `IntentType.QUESTION` — verify brain is called, tts is called, memory stub is called
- Test the `CLICK_COMMAND` path — verify clicker is called and brain is NOT called
- Test the `STOP` path — verify loop exits cleanly

### Unit Tests — `test_action_executor.py`
- Mock `pyautogui` and `subprocess`
- Test `CLICK` calls `pyautogui.click` with correct coordinates from `element.center`
- Test `TYPE_TEXT` calls `pyautogui.write` with the correct string
- Test `PRESS_KEY` calls `pyautogui.press` with the correct key
- Test `HOTKEY` calls `pyautogui.hotkey` with unpacked keys
- Test `OPEN_APP` calls `subprocess.Popen` with the app name
- Test `SEQUENCE` executes all steps in order with correct waits
- Test `ClickOutOfBoundsError` raised for out-of-bounds coordinates

### Integration Tests — `test_full_pipeline.py`
- `@pytest.mark.integration`
- Real voice input → transcription → intent classification → screen read → Claude API → overlay + TTS
- Requires all API keys and `RUN_INTEGRATION=true`

---

## Running Locally

After this phase, `python main.py` runs the full pipeline end-to-end:

```
python main.py
```

Expected: Wake on "Hey Krithika", ask "where is the File menu in Notepad?", see a highlight drawn on the File menu and hear Krithika describe it.

---

## Definition of Done

- `python main.py` starts cleanly and reaches the "ready" state
- Full voice → overlay + TTS loop works for at least `QUESTION`, `SCREEN_QUERY`, and `CLICK_COMMAND` intents
- Switching `brain.provider` in `config.yaml` from `claude` to `ollama` works without code changes
- Click-on-command executes immediately after Krithika announces it
- App-specific prompt is loaded when the active app matches a `prompts/` file
- All unit tests pass in CI

---

## Success Criteria

1. End-to-end: say "Hey Krithika, help me import footage in DaVinci Resolve" → Krithika speaks step-by-step instructions and highlights the relevant UI elements
2. Click: say "Hey Krithika, click File" in Notepad → Krithika announces "Clicking File" and the File menu opens
3. Provider swap: change `config.yaml` to `provider: ollama`, restart → Krithika works using the local model (slower but functional)
4. All unit tests pass; integration test passes with real API keys

---

## Checklist

- [ ] `adapter.py` — `BrainAdapter` ABC, `BrainContext`, `BrainResponse` defined
- [ ] `claude_adapter.py` — full implementation with streaming + structured output
- [ ] `ollama_adapter.py` — full implementation
- [ ] `gemini_adapter.py` — stub or full
- [ ] `openai_adapter.py` — stub or full
- [ ] `factory.py` — `create_brain_adapter` factory
- [ ] `action_executor.py` — `ActionExecutor` with all 8 action types, FAILSAFE, bounds check
- [ ] `config.py` — `KrithikaConfig` with Pydantic BaseSettings
- [ ] `orchestrator.py` — full async loop with all 7 intent paths handled
- [ ] `main.py` — full entry point wiring all components
- [ ] `prompts/system_base.txt` written
- [ ] `prompts/davinci_resolve.txt` and at least 2 more app prompts written
- [ ] Memory stub injected (no-op, replaced in Phase 5)
- [ ] Unit tests written and passing
- [ ] Integration test written
- [ ] End-to-end demo working
- [ ] CI pipeline passes

---

## Conclusion

> *To be filled after completion.*
> Document adapter performance differences between Claude and Ollama, any issues with PyQt6/asyncio threading, app-specific prompt effectiveness, and anything Phase 5 needs to know.
