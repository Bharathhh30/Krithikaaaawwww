# Phase 2 — Intent Router & Screen Reading

## Overview

Build the classification and screen-reading layer. Before any expensive AI call is made, every voice command is classified by TypeSafe Jev into a typed intent. Screen content is read using Windows UI Automation first (free), falling back to OmniParser and then Claude Vision only when needed. This is the cost-control engine of the system.

---

## What We're Building

| Component | Purpose |
|---|---|
| Intent router | Classifies voice commands into typed intents using TypeSafe Jev |
| UIA screen reader | Reads UI elements from the accessibility tree — no AI, no screenshots |
| Screenshot capturer | Captures and crops screen when UIA is insufficient |
| OmniParser integration | Parses screenshots into element bounding boxes locally |
| Element selector | Uses Jev to pick the right element from a list of candidates |

---

## Files to Create

```
krithika/
└── intent/
    ├── __init__.py
    ├── router.py           # TypeSafe Jev intent classification
    ├── schemas.py          # Pydantic dataclasses for intents and results
    └── element_selector.py # Jev-based element selection from UIA list

krithika/
└── screen/
    ├── __init__.py
    ├── capture.py          # mss screenshot + window crop
    ├── uia_reader.py       # pywinauto UIA accessibility tree
    └── omniparser.py       # OmniParser ONNX model wrapper

tests/unit/
├── test_intent_router.py
├── test_uia_reader.py
└── test_element_selector.py

tests/integration/
└── test_screen_reading.py
```

---

## Implementation Details

### `schemas.py` — Data Models

```python
from dataclasses import dataclass
from enum import Enum

class IntentType(str, Enum):
    QUESTION       = "question"
    SCREEN_QUERY   = "screen_query"
    CLICK_COMMAND  = "click_command"       # "Krithika click the Save button"
    ACTION_COMMAND = "action_command"      # "open terminal", "type hello", "press enter", sequences
    FOLLOW_UP      = "follow_up"
    MEMORY_RECALL  = "memory_recall"
    TASK_START     = "task_start"
    STOP           = "stop"

@dataclass
class ClassifiedIntent:
    intent: IntentType
    needs_screen: bool
    target_element: str | None   # filled for CLICK_COMMAND
    confidence: float            # from Jev

@dataclass
class UIElement:
    name: str
    role: str                    # "Button", "MenuItem", "Edit", etc.
    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)

@dataclass
class ScreenReaderResult:
    elements: list[UIElement]
    source: str                  # "uia" | "omniparser" | "vision"
    screenshot: bytes | None     # populated for omniparser/vision paths
```

### `router.py` — IntentRouter

```python
from typesafe_sdk import TypeSafeClient, Choice, Noul

class IntentRouter:
    def __init__(self, api_key: str) -> None:
        self._client = TypeSafeClient(api_key=api_key)

    async def classify(
        self,
        user_text: str,
        active_app: str,
        working_memory: dict,
    ) -> ClassifiedIntent:
        """Classify the intent of a voice command using TypeSafe Jev."""
```

Questions sent to Jev in a single request:
- `intent`: `Choice` over the 8 `IntentType` values
- `needs_screen`: `Noul` — "Does answering this require looking at the screen?"

**`action_command` vs `click_command`**: Jev should return `click_command` only when the user names a specific visible UI element ("click the Save button"). Use `action_command` for everything else — opening apps, typing text, pressing keys, keyboard shortcuts, and multi-step sequences ("open terminal and type claude and press enter").

Run in `ThreadPoolExecutor` to stay non-blocking. If Jev confidence < 0.4, return `IntentType.QUESTION` as safe fallback.

### `element_selector.py` — ElementSelector

```python
class ElementSelector:
    async def select(
        self,
        command: str,
        elements: list[UIElement],
    ) -> UIElement | None:
        """Use Jev Choice to select the most likely target element. Returns None if no match."""
```

- Build `Choice` criteria dynamically from `[e.name for e in elements]`
- If confidence < 0.6, return `None` — caller will escalate to Vision
- If `elements` is empty, return `None` immediately without calling Jev

### `uia_reader.py` — UIAReader

```python
from pywinauto import Application

class UIAReader:
    def get_elements(self, hwnd: int) -> list[UIElement]:
        """Return all interactive elements in the given window via Windows UI Automation."""
```

- Connect with `Application(backend="uia").connect(handle=hwnd)`
- Filter to actionable roles: `Button`, `MenuItem`, `Edit`, `CheckBox`, `RadioButton`, `ComboBox`, `Hyperlink`
- Return empty list (not error) if window is not accessible — callers handle fallback
- Cache results per `hwnd` for 10 seconds — UIA calls take ~50ms each

### `capture.py` — ScreenCapture

```python
class ScreenCapture:
    def capture_window(self, hwnd: int) -> bytes:
        """Capture and return the active window as JPEG bytes (1280×720 max, quality 80)."""

    def capture_region(self, x: int, y: int, width: int, height: int) -> bytes:
        """Capture a specific screen region."""
```

- Use `mss` for capture (<10ms)
- Crop to window bounds using `pywin32` `win32gui.GetWindowRect`
- Resize to fit within 1280×720 while maintaining aspect ratio
- Encode as JPEG quality 80 to minimise Vision API token cost

### `omniparser.py` — OmniParserReader

```python
class OmniParserReader:
    def parse(self, image_bytes: bytes) -> list[UIElement]:
        """Run OmniParser on image bytes. Returns detected elements with bounding boxes."""
```

- Load the OmniParser ONNX model once at init
- Return empty list on parse failure — never raise to caller
- Each result mapped to `UIElement` with `source="omniparser"`

---

## Tiered Screen Reading — How Callers Use It

The orchestrator always calls in this order:

```python
# 1. Try UIA (free)
elements = uia_reader.get_elements(active_hwnd)

# 2. If empty, try OmniParser on screenshot
if not elements:
    screenshot = screen_capture.capture_window(active_hwnd)
    elements = omniparser.parse(screenshot)

# 3. If still empty/low confidence, pass screenshot to Claude Vision (Phase 4)
if not elements:
    # escalate to brain — handled in Phase 4
```

---

## Dependencies to Add with uv

```powershell
uv add "typesafe-sdk>=1.0.0" "pywinauto>=0.6.8" "pywin32>=306" "mss>=9.0.1" "Pillow>=10.0.0" "onnxruntime>=1.17.0"
```

Commit the resulting `pyproject.toml` and `uv.lock` changes together.

OmniParser model weights must be downloaded separately (see README instructions). Store in `models/omniparser/`.

---

## Testing Requirements

### Unit Tests — `test_intent_router.py`
- Mock the TypeSafe SDK client
- Test that each `IntentType` is returned correctly for representative inputs
- Test that low-confidence results fall back to `IntentType.QUESTION`
- Test that `needs_screen=False` for pure knowledge questions

### Unit Tests — `test_uia_reader.py`
- Mock `pywinauto.Application` — do not require a real window
- Test that elements outside the role filter are excluded
- Test that an inaccessible window returns an empty list without raising

### Unit Tests — `test_element_selector.py`
- Mock TypeSafe SDK client
- Test correct selection from a list of 5 elements
- Test that low confidence returns `None`
- Test that empty element list returns `None` without calling Jev

### Integration Tests — `test_screen_reading.py`
- `@pytest.mark.integration`
- Opens a real Windows Notepad window and verifies UIA returns at least the text area and menu bar
- Requires `RUN_INTEGRATION=true` env variable to run

---

## Running Locally

After this phase, add a `--test-intent` flag to `main.py`:

```
python main.py --test-intent
```

This starts the voice pipeline and prints the classified intent for every utterance instead of routing it. Lets you verify Jev is classifying correctly before the full pipeline is wired.

---

## Definition of Done

- TypeSafe Jev correctly classifies all 7 intent types for representative test inputs
- UIA reader returns elements for Notepad, File Explorer, and a browser window
- OmniParser loads and runs without error on a test screenshot
- Element selector picks the correct button from a known list with confidence ≥ 0.8
- All unit tests pass in CI
- No TypeSafe API calls are made for `IntentType.STOP` (handled as a local shortcut)

---

## Success Criteria

1. Say "Hey Krithika, where is the Save button?" in Notepad → intent classified as `screen_query`, UIA returns the menu bar elements, Jev selects "File > Save" — no screenshot sent to any API
2. Say "Hey Krithika, what is color grading?" → classified as `question`, `needs_screen=False`, no screen read triggered
3. Say "Hey Krithika, stop" → classified as `stop` immediately, no Jev call made
4. UIA read + Jev classification completes in under 500ms total

---

## Checklist

- [ ] `schemas.py` — all dataclasses defined with type hints
- [ ] `router.py` — `IntentRouter` using TypeSafe Jev with Choice + Noul
- [ ] `element_selector.py` — `ElementSelector` with dynamic Choice criteria
- [ ] `uia_reader.py` — `UIAReader` with role filter and 10-second cache
- [ ] `capture.py` — `ScreenCapture` with window crop and JPEG resize
- [ ] `omniparser.py` — `OmniParserReader` with ONNX model
- [ ] OmniParser model weights downloaded and documented in README
- [ ] Unit tests written and passing
- [ ] Integration test written (gated on `RUN_INTEGRATION=true`)
- [ ] `--test-intent` mode added to `main.py`
- [ ] CI pipeline passes

---

## Conclusion

> *To be filled after completion.*
> Document Jev classification accuracy on real utterances, OmniParser performance on typical app screenshots, any UIA limitations discovered, and what needs to be communicated to Phase 3.
