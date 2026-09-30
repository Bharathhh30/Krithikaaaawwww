# Phase 3 — Visual Guidance Overlay

## Overview

Build the visual layer that sits transparently on top of every application. When Krithika identifies a UI element, the overlay draws a pulsing highlight box and animated arrow pointing directly at it — on any monitor. A floating HUD panel shows Krithika's current state (listening, thinking, speaking). The user never has to wonder if Krithika heard them.

---

## What We're Building

| Component | Purpose |
|---|---|
| Transparent overlay window | Full-screen transparent PyQt6 window always on top of every app |
| Highlight box | Animated pulsing rectangle drawn around the target element |
| Arrow | Animated arrow that routes from the HUD panel to the target |
| HUD panel | Small floating status panel showing listening / thinking / speaking state |
| Multi-monitor support | One overlay window per connected display |
| Step counter | "Step 2 of 5" indicator for multi-step guidance |

---

## Files to Create

```
krithika/
└── overlay/
    ├── __init__.py
    ├── app.py              # QApplication lifecycle manager
    ├── window.py           # Transparent overlay QWidget per monitor
    ├── highlight.py        # HighlightSpec dataclass + drawing logic
    ├── arrow.py            # Animated arrow painter
    ├── hud.py              # Floating HUD panel (listening/thinking/speaking)
    └── monitor.py          # Multi-monitor detection and window management

tests/unit/
└── test_highlight.py
```

---

## Implementation Details

### `monitor.py` — MonitorManager

```python
from screeninfo import get_monitors
from dataclasses import dataclass

@dataclass
class MonitorInfo:
    index: int
    x: int
    y: int
    width: int
    height: int
    is_primary: bool

class MonitorManager:
    def get_all(self) -> list[MonitorInfo]: ...
    def get_primary(self) -> MonitorInfo: ...
    def monitor_for_point(self, x: int, y: int) -> MonitorInfo: ...
```

### `window.py` — OverlayWindow

One `OverlayWindow` per monitor. Each is a `QWidget` configured as:

```python
self.setWindowFlags(
    Qt.WindowType.FramelessWindowHint |
    Qt.WindowType.WindowStaysOnTopHint |
    Qt.WindowType.Tool |           # doesn't show in taskbar
    Qt.WindowType.WindowTransparentForInput  # mouse clicks pass through
)
self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
```

The window is positioned to exactly cover its assigned monitor. It is completely transparent and click-through — it only draws, never intercepts input.

```python
class OverlayWindow(QWidget):
    def show_highlight(self, spec: HighlightSpec) -> None: ...
    def clear(self) -> None: ...
    def paintEvent(self, event: QPaintEvent) -> None:
        """Draw current highlight and arrow using QPainter."""
```

### `highlight.py` — HighlightSpec + Animation

```python
@dataclass
class HighlightSpec:
    x: int
    y: int
    width: int
    height: int
    label: str
    animation: str = "pulse"   # "pulse" | "static"
```

Drawing behaviour:
- **Pulse animation**: rectangle border animates between 2px and 4px stroke width, with opacity 0.6 → 1.0 → 0.6, cycling every 800ms using `QPropertyAnimation`
- **Colour**: bright cyan `#00E5FF` — high contrast against any application background
- **Corner handles**: small squares at each corner of the rectangle for extra visibility
- **Label**: element name drawn above the rectangle in white text with dark background

### `arrow.py` — ArrowPainter

- Draws a bezier curve from the HUD panel edge to the centre of the highlighted element
- Animated: dashes travel along the curve using `QPropertyAnimation` on a dash offset
- Colour matches the highlight: `#00E5FF`
- Arrow head at the target end

### `hud.py` — HUDPanel

A small always-on-top panel (default top-right corner of primary monitor, 240×80px):

```python
class HUDPanel(QWidget):
    def set_state(self, state: Literal["idle", "listening", "thinking", "speaking"]) -> None: ...
    def show_step(self, current: int, total: int) -> None: ...
    def hide_step(self) -> None: ...
```

Visual states:
- **Idle**: small "K" icon, dim
- **Listening**: mic icon + pulsing green ring
- **Thinking**: spinning indicator
- **Speaking**: audio waveform animation

The HUD is also click-through but includes a small drag handle so the user can reposition it by voice command ("Krithika move panel to bottom right") — implement drag support even if the voice command comes in a later phase.

### `app.py` — OverlayApp

Manages the `QApplication` instance and all overlay windows. Must run in its own thread because Qt requires the GUI to live on the main thread — but the rest of Krithika is asyncio. Use `QThread` or spawn the Qt loop in a dedicated OS thread and communicate via thread-safe signals/slots.

```python
class OverlayApp:
    def start(self) -> None:
        """Start the Qt event loop in a background thread."""

    def highlight(self, spec: HighlightSpec) -> None:
        """Thread-safe: show a highlight on the correct monitor."""

    def clear(self) -> None:
        """Thread-safe: remove all highlights."""

    def set_hud_state(self, state: str) -> None:
        """Thread-safe: update the HUD panel state."""
```

Use `QMetaObject.invokeMethod` with `Qt.ConnectionType.QueuedConnection` for thread-safe calls from the asyncio loop into the Qt thread.

---

## Dependencies to Add with uv

```powershell
uv add "PyQt6>=6.6.0" "screeninfo>=0.8.1"
```

Commit the resulting `pyproject.toml` and `uv.lock` changes together.

---

## Testing Requirements

### Unit Tests — `test_highlight.py`
- Test `HighlightSpec` default values
- Test that `monitor_for_point` returns the correct monitor for coordinates on each screen
- Test that `OverlayWindow.show_highlight` sets internal state correctly (mock `QPainter`)

### Manual Visual Test (required — cannot be automated)
Run the overlay demo script:
```
python scripts/overlay_demo.py
```
This script:
1. Opens a Notepad window
2. Shows a highlight at the "File" menu position (hardcoded coordinates)
3. Cycles through all HUD states every 2 seconds
4. Runs for 10 seconds then exits

Expected: Pulsing cyan box on Notepad's File menu, animated arrow from HUD, HUD cycling through states.

---

## Running Locally

```
python scripts/overlay_demo.py
```

Also verify multi-monitor works if a second display is connected:
- The overlay window appears on each monitor
- A highlight on monitor 2 draws on the monitor 2 overlay window, not monitor 1

---

## Definition of Done

- Transparent overlay window covers the full primary monitor without blocking any clicks on apps underneath
- Highlight box appears at the correct screen coordinates and pulses
- Arrow correctly routes from HUD to the highlight target
- HUD panel shows correct state icons for idle / listening / thinking / speaking
- All overlay windows are removed cleanly when Krithika exits (no ghost windows)
- Multi-monitor: a second connected monitor gets its own overlay window
- All unit tests pass in CI (GUI tests skipped in headless CI with `@pytest.mark.skipif(os.environ.get("CI") == "true", ...)`)

---

## Success Criteria

1. Open any application (Notepad, browser, etc.) and run the overlay demo — the highlight draws on top of the app without the app losing focus or receiving stray clicks
2. Disconnect and reconnect a monitor — Krithika detects the change and adds/removes overlay windows accordingly
3. HUD panel is visible and updates state in real time during a voice interaction

---

## Checklist

- [ ] `monitor.py` — `MonitorManager` using `screeninfo`
- [ ] `window.py` — transparent click-through `OverlayWindow` per monitor
- [ ] `highlight.py` — `HighlightSpec` + pulse animation
- [ ] `arrow.py` — bezier curve animated arrow
- [ ] `hud.py` — `HUDPanel` with 4 states + step counter
- [ ] `app.py` — `OverlayApp` with thread-safe Qt ↔ asyncio bridge
- [ ] `scripts/overlay_demo.py` created for manual testing
- [ ] Multi-monitor support verified manually
- [ ] Click-through verified (apps underneath remain interactive)
- [ ] Unit tests written and passing
- [ ] CI skips GUI tests in headless environment
- [ ] CI pipeline passes

---

## Conclusion

> *To be filled after completion.*
> Document any Qt/asyncio threading issues encountered, multi-monitor edge cases, performance of animations on Intel Arc, and anything Phase 4 needs to know about calling the overlay API.
