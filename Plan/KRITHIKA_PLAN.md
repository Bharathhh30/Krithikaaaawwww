**Version: 3.0** | Last updated: 2026-09-30

---

# Krithika — Voice-Controlled AI Screen Partner
### Full Architecture & Build Plan

---

## Vision

Build a fully voice-operated AI companion that lives on your Windows screen. You never touch the keyboard or mouse. You speak; Krithika listens, sees your screen, understands what you're doing, and guides you step-by-step — pointing to exact UI elements with visual arrows and overlays. Krithika becomes a real partner: it knows your history, learns your workflows, and guides you through any software or task you don't know how to do.

---

## Reference: "Clicky" by Farza Majeed

Clicky is the closest known public demo. Key learnings:
- It sits alongside your cursor and watches your screen
- You ask it questions ("How do I make this more cinematic?") and it points to the exact button/menu
- It uses a vision model + LLM to understand the screen and provide coordinates
- It demonstrated in DaVinci Resolve (video editing) — exactly the "I don't know the software" use case

**Our delta**: Clicky is keyboard/mouse operated. We go fully voice-only, add persistent memory (Obsidian), multi-provider AI brain, type-safe routing, and build Windows-native with always-on overlay.

---

## High-Level Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│                          KRITHIKA SYSTEM                              │
│                                                                       │
│  ┌──────────┐   ┌───────────────────┐   ┌──────────────────────────┐ │
│  │  VOICE   │──▶│  INTENT ROUTER    │──▶│  AI BRAIN                │ │
│  │  INPUT   │   │  (Type-safe/Instr)│   │  (Multi-Provider Adapter)│ │
│  └──────────┘   └─────────┬─────────┘   └────────────┬─────────────┘ │
│                            │                          │               │
│  ┌──────────┐   ┌──────────▼─────────┐   ┌──────────▼─────────────┐ │
│  │  SCREEN  │──▶│  UI READER         │   │  VISUAL OVERLAY         │ │
│  │  CAPTURE │   │  (UIA → Screenshot)│   │  (Arrows + Highlight)   │ │
│  └──────────┘   └────────────────────┘   └────────────────────────┘ │
│                                                                       │
│  ┌─────────────────────┐   ┌──────────────────┐                      │
│  │   VOICE OUTPUT      │   │   MEMORY         │                      │
│  │   (TTS)             │   │   (Obsidian)     │                      │
│  └─────────────────────┘   └──────────────────┘                      │
└───────────────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Voice Input Pipeline

**Purpose**: Convert speech to intent — the only way the user interacts.

| Sub-component | Role | Technology |
|---|---|---|
| Wake word | "Hey Krithika" always-on listener | Picovoice Porcupine (free tier) |
| Audio capture | Microphone stream | `sounddevice` (lower latency than PyAudio) |
| VAD | Auto-stop recording on silence | Silero VAD |
| Speech-to-Text | Convert audio to text | OpenAI Whisper (`small`, runs locally) |

**Flow**:
```
Microphone → Wake word detected → Record until silence →
Whisper transcribes → Send text to Intent Router
```

**Key decisions**:
- Run Whisper locally — `whisper-small` on your Core Ultra 5 = ~1.5s, no network round-trip
- Silero VAD auto-detects end of speech; no manual "stop" needed
- Porcupine wake word runs at <1% CPU continuously

---

### 2. Intent Router (TypeSafe Jev)

**Purpose**: Classify every voice command into a typed intent before routing — avoids sending every query to an expensive vision model.

**Technology**: **TypeSafe Jev** — a System One model that returns typed judgments and calibrated probabilities rather than generating text. It is specifically designed for exactly this use case: fast, programmable common sense where code owns the workflow and the model supplies semantic understanding.

**Why Jev over a general LLM**:
- Purpose-built for classification, not text generation — returns `Choice`, `Noul`, and `Score` typed answers
- Returns calibrated probabilities alongside the answer — enables confidence-gated routing
- Multiple questions answered in a single request (parallel, not sequential)
- Significantly cheaper and faster than routing a classification question through Claude/GPT
- Model cannot hallucinate outside defined criteria

**Intent classification with Jev**:
```python
from typesafe_sdk import TypeSafeClient, Choice, Noul

client = TypeSafeClient()  # uses TYPESAFE_API_KEY env var

result = client.system_one(
    state={"user_voice": user_text, "active_app": active_app, "context": working_memory},
    questions={
        "intent": Choice(
            instructions="What is the user trying to do?",
            criteria={
                "question":       "User is asking a knowledge or how-to question",
                "screen_query":   "User wants to locate or understand something on screen",
                "click_command":  "User explicitly wants to click a specific UI element",
                "follow_up":      "User is acknowledging a step or continuing ('ok', 'done', 'then what')",
                "memory_recall":  "User is asking about past sessions or what they did before",
                "task_start":     "User is starting a new multi-step workflow or task",
                "stop":           "User wants to cancel or stop what Krithika is doing",
            }
        ),
        "needs_screen": Noul(
            instructions="Does answering this require looking at the current screen state?"
        ),
        "target_element": Choice(
            instructions="If this is a click command, what is the target element name? Return 'none' if not a click.",
            criteria={"none": "Not a click command or target unclear"}
            # additional criteria injected dynamically from UIA element list
        )
    }
)

intent = result.intent.choice          # e.g. "click_command"
needs_screen = result.needs_screen.noul > 0.6  # probability threshold
confidence = result.intent.confidence
```

**Routing table**:

| Intent | Screen needed | Next step | Cost tier |
|---|---|---|---|
| `question` | No | Memory lookup → AI Brain (no vision) | Very low |
| `memory_recall` | No | ChromaDB search → AI Brain | Very low |
| `follow_up` | No | Working memory update | Near zero |
| `screen_query` | Yes → UIA first | UIA elements → Jev element picker → Vision fallback | Low |
| `click_command` | Yes → UIA first | UIA elements → Jev element picker → click | Low |
| `task_start` | Yes | Full AI Brain (vision) | Medium |
| `stop` | No | Direct handler | Zero |

**Confidence routing**: If `intent.confidence < 0.5`, Krithika asks for clarification rather than routing to a handler with uncertain intent.

**UI element selection via Jev** (avoids vision call for most clicks):
```python
# UIA gives us the element list for the active window
elements = ["Cancel", "Approve", "Save Draft", "Help"]

# Ask Jev to pick the right one — no LLM, no screenshot needed
result = client.system_one(
    state={"command": "click the approve button", "elements": elements},
    questions={
        "target": Choice(
            instructions="Which element does the user want to click?",
            criteria={name: f"The '{name}' element" for name in elements}
        )
    }
)
target_name = result.target.choice       # "Approve"
target_confidence = result.target.confidence  # 0.97
```

---

### 3. Screen Intelligence (Tiered UI Reading)

**Purpose**: Get the position of UI elements — prioritising the cheapest method first.

**Three-tier fallback chain**:

```
Tier 1: Windows UI Automation (UIA) ──── Fast, free, no AI
    ↓ (if app not accessible)
Tier 2: OmniParser on screenshot ──────── Medium cost, no LLM
    ↓ (if parsing confidence low)
Tier 3: Claude Vision + screenshot ─────── Full LLM, highest accuracy
```

#### Tier 1 — Windows UI Automation (UIA)

Windows exposes a full accessibility tree for all Win32, WPF, Office, browser, and File Explorer windows. This is what screen readers use. It gives element names, roles, bounding boxes, and interaction handles — **no screenshot, no AI cost**.

```python
import pywinauto
from pywinauto import Application

app = Application(backend="uia").connect(handle=foreground_hwnd)
all_elements = app.top_window().descendants(control_type="Button")
# Returns: [Button("Import Media", rect=(245,180,365,215)), Button("Export", ...), ...]
```

- Works for: all Win32 apps, WPF, Office, File Explorer, Settings, browsers
- Fails for: games, some Electron apps, heavily custom-rendered UIs
- Cost: **zero**

After getting elements from UIA, pass the name list to the **Instructor classifier** (Section 2) to pick the right one. No vision model needed.

#### Tier 2 — OmniParser

Microsoft's open-source model for parsing screenshots into UI element bounding boxes. Run locally on CPU.

- Use when UIA returns an empty or incomplete tree
- Returns: element type, label, bounding box
- Cost: local inference (~300ms on your CPU)

#### Tier 3 — Claude Vision

Full screenshot sent to Claude claude-sonnet-5 vision model. Use as last resort.

- Use when OmniParser confidence is below threshold
- Use when the screen context itself is needed for reasoning (not just "where is button X")
- Cost: highest (~$0.008 per screenshot at 1280×720)

**Smart screenshot strategy** (when screenshot IS needed):
- Crop to active window, not full desktop
- Resize to 1280×720 JPEG 80% quality (~4× token reduction)
- Cache: same window + no state change → reuse last screenshot for 10 seconds

| Sub-component | Technology |
|---|---|
| Screenshot capture | `mss` (<10ms) |
| Active window detection | `pywin32` (`win32gui.GetForegroundWindow`) |
| UIA accessibility tree | `pywinauto` (backend="uia") |
| OmniParser | Microsoft OmniParser (local ONNX model) |
| Multi-monitor detection | `screeninfo` + `pywin32` |

**Multi-monitor support**:
- `screeninfo.get_monitors()` returns all connected displays
- Overlay spawns a transparent window on each monitor
- UIA and screenshot capture work per-monitor
- Krithika defaults to the active monitor; user can say "look at my left screen"

---

### 4. AI Brain (Multi-Provider Adapter)

**Purpose**: Understand the user's request in full context and generate guidance. Abstracted behind a provider-agnostic adapter so any LLM can be the brain.

**Adapter interface**:
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class BrainContext:
    user_query: str
    screenshot: bytes | None       # only if needed
    ui_elements: list[UIElement]   # from UIA/OmniParser
    working_memory: dict
    retrieved_memory: str
    active_app: str

@dataclass
class BrainResponse:
    speak: str                     # what Krithika says
    highlight: HighlightSpec | None  # what to draw on screen
    click_target: str | None       # element name to click (if requested)
    next_step: str | None
    memory_write: dict | None

class BrainAdapter(ABC):
    @abstractmethod
    async def process(self, context: BrainContext) -> BrainResponse:
        pass
```

**Provider implementations**:

| Adapter | Provider | When to use |
|---|---|---|
| `ClaudeAdapter` | Anthropic (claude-sonnet-5) | Default — best vision + reasoning |
| `GeminiAdapter` | Google Gemini 2.0 Flash | If user has Google AI key |
| `OpenAIAdapter` | OpenAI GPT-4o | If user has OpenAI key |
| `OllamaAdapter` | Local Ollama (LLaVA, Llava-next) | Fully offline / privacy mode |
| `AzureAdapter` | Azure OpenAI | Enterprise users |

**Configuration** (`config.yaml`):
```yaml
brain:
  provider: claude          # swap to gemini, openai, ollama, azure
  model: claude-sonnet-5
  api_key_env: ANTHROPIC_API_KEY

classifier:
  provider: claude          # usually same or cheaper model
  model: claude-haiku-4-5
```

**System prompt** (injected per request):
```
You are Krithika, a voice-operated AI partner on the user's Windows 11 machine.
You can see the screen and the list of UI elements. The user CANNOT use keyboard or mouse.
Always respond with:
1. A spoken response (clear, concise — will be read aloud)
2. Optional: which UI element to highlight
3. Optional: which element to click (only if user explicitly said "click X")
4. Optional: memory to save

Active app: {active_app}
Current task: {working_memory}
Relevant memory: {retrieved_memory}
UI elements available: {ui_elements_json}
```

**Structured output** (parsed by orchestrator):
```json
{
  "speak": "Click the Import Media button in the top-left of the timeline panel",
  "highlight": {
    "element_name": "Import Media",
    "x": 245, "y": 180, "width": 120, "height": 35,
    "animation": "pulse"
  },
  "click_target": null,
  "next_step": "A file browser will open — tell me when you see it.",
  "memory_write": {
    "task": "Learning DaVinci Resolve",
    "step_completed": "Located Import Media",
    "next_step": "Select footage files"
  }
}
```

---

### 5. Click-on-Command

**Purpose**: Krithika clicks a UI element when the user explicitly says to. Never automatic.

**Trigger**: User says "Krithika click [element]" → Intent Router classifies as `CLICK_COMMAND`

**Flow**:
```
User: "Krithika click the Approve button"
  → IntentRouter: CLICK_COMMAND, target="Approve button"
  → UIA tree: find element named "Approve" → get bounding box
  → Instructor classifier confirms match (if multiple candidates)
  → Overlay: highlight the target element
  → Krithika speaks: "Clicking Approve"
  → pyautogui.click(center_x, center_y)
  → Screenshot to confirm action completed
```

**Technology**: `pyautogui` for click execution

**Behavior**:
- Highlight the element and announce ("Clicking Approve") then click immediately — no delay, user already confirmed by speaking the command
- If multiple matching elements found, Krithika asks: "I see two Approve buttons — toolbar or dialog?" and waits for user to clarify before clicking

---

### 6. Visual Guidance Overlay

**Purpose**: Draw visual arrows, highlight boxes, and step indicators on top of any application.

**Technology**: **PyQt6** with `Qt.WindowStaysOnTopHint` + `Qt.WA_TranslucentBackground`

**Features**:

| Feature | Description |
|---|---|
| Pulsing highlight box | Animated rectangle around target element |
| Animated arrow | Routes from Krithika panel to target |
| Step counter | "Step 2 of 5" |
| Listening indicator | Mic-active visual pulse |
| Krithika panel | Small floating HUD (top-right corner, collapsible) |
| Multi-monitor | Overlay window spawned per monitor |

**Overlay placement**:
- Panel: top-right corner by default, draggable
- Collapses to a small icon when idle
- Arrow dynamically routes to avoid covering the target

---

### 7. Text-to-Speech Output

**Purpose**: Krithika speaks every response.

| Layer | Use case | Technology |
|---|---|---|
| Instant (local) | Acknowledgments: "Got it", "Looking..." | Windows SAPI via `pyttsx3` |
| Quality (cloud) | Full instructions | ElevenLabs Turbo (streaming) |

**Streaming**: ElevenLabs WebSocket streaming — first audio chunk in ~300ms while rest is still generating.

**Voice**: Specific voice requirements to be provided by user in Phase 4. ElevenLabs supports voice cloning — can use any provided audio sample.

---

### 8. Memory System (Obsidian)

**Purpose**: Krithika's long-term brain — persists history, structured knowledge, and task state across all sessions.

**Three-layer architecture**:

#### Layer 1 — Raw History (Episodic)
- Every command, response, action, and screenshot hash
- **SQLite** (`history.db`) — never deleted
```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    timestamp DATETIME,
    user_voice TEXT,
    krithika_response TEXT,
    active_app TEXT,
    screenshot_hash TEXT,
    ui_elements JSON,
    actions_taken JSON
);
```

#### Layer 2 — Semantic Search (Vector)
- Embeddings of all past interactions
- "What did Krithika tell me about DaVinci Resolve last week?"
- **ChromaDB** (local, no server, zero config)
- Auto-populated from Layer 1 at session end

#### Layer 3 — Structured Wiki (Obsidian Vault)

The wiki lives as an **Obsidian vault** rooted at the user's home directory — not inside the project folder. This keeps memory independent of the codebase, always reachable from any terminal session, and persistent across project moves or reinstalls.

**Vault location**:
```
%USERPROFILE%\KrithikaMemory\
```
Which resolves to:
```
C:\Users\VasarlaNagaSaiBharat\KrithikaMemory\
```

In code, always resolve dynamically:
```python
import os
VAULT_PATH = os.path.join(os.path.expanduser("~"), "KrithikaMemory")
```

**Vault structure**:
```
C:\Users\VasarlaNagaSaiBharat\KrithikaMemory\
├── Apps/
│   ├── DaVinci_Resolve/
│   │   ├── Importing_Media.md        ← auto-written by Krithika
│   │   ├── Color_Grading_Basics.md
│   │   └── Index.md
│   ├── Photoshop/
│   └── Windows_Settings/
├── Tasks/
│   ├── Active.md                     ← current task + steps
│   └── Completed/
│       └── 2026-09-30_Import_Footage.md
└── My_Workflows.md
```

**Integration**: Krithika creates `KrithikaMemory/` on first run if it doesn't exist, then writes Markdown files directly via Python file I/O. The user points Obsidian at this folder as a vault — no plugin needed for Krithika to write to it.

**Optional**: Obsidian Local REST API plugin — allows Krithika to also read vault content through HTTP, enabling backlink-aware retrieval.

#### Working Memory (Session)
- Current task, step number, active app — Python dict in-process
- Snapshot to disk every 30 seconds
- Restored on restart

**Memory retrieval flow**:
```
User speaks →
1. Working memory (current session) → instant
2. ChromaDB semantic search (similar past interactions) → <200ms
3. Obsidian wiki for active app → file read <50ms
4. Top-3 results injected into AI Brain context
```

---

### 9. Orchestrator / Main Loop

**Technology**: Python `asyncio`

```python
async def main_loop():
    while True:
        await wake_word_detected()                      # always-on thread

        screenshot_task = asyncio.create_task(capture_screen())
        audio = await record_until_silence()
        text = await whisper_transcribe(audio)

        overlay.show_thinking()

        # Cheap classification first — TypeSafe Jev
        intent = await classifier.classify(text)        # Jev Choice + Noul

        if intent.type == IntentType.STOP:
            await handle_stop(); continue

        if intent.needs_screen:
            # Try UIA first (free)
            elements = await uia.get_elements(active_hwnd)
            if not elements:
                screenshot = await screenshot_task       # use screenshot
                elements = await omniparser.parse(screenshot)
        else:
            screenshot_task.cancel()                    # don't waste the call

        if intent.type == IntentType.CLICK_COMMAND:
            target = await classifier.choose_element(intent.target_element, elements)
            await overlay.highlight(target)
            await tts.speak(f"Clicking {target.element_name}")
            await clicker.click(target)
            continue

        memory_context = await memory.retrieve(text, active_app)

        response = await brain.process(BrainContext(
            user_query=text,
            screenshot=screenshot if intent.needs_screen else None,
            ui_elements=elements,
            working_memory=session.state,
            retrieved_memory=memory_context,
            active_app=active_app
        ))

        await asyncio.gather(
            tts.speak(response.speak),
            overlay.highlight(response.highlight)
        )

        await memory.write(text, response, active_app)
```

---

## Full Tech Stack

| Category | Technology | Reason |
|---|---|---|
| Language | Python 3.12 | Ecosystem, async, AI library support |
| Wake word | Picovoice Porcupine | <1% CPU, offline, free tier |
| Audio capture | `sounddevice` | Lower latency than PyAudio |
| VAD | Silero VAD | Auto-stop on silence |
| Speech-to-Text | OpenAI Whisper (`small`, local) | ~1.5s on CPU, no API cost |
| Intent classification | **TypeSafe Jev** (System One model) | Purpose-built for typed judgments, calibrated probabilities, cheaper than LLM classification |
| UI reading (primary) | `pywinauto` (UIA backend) | Free, no AI, works for all native apps |
| UI reading (secondary) | OmniParser (Microsoft, local ONNX) | Open-source, no API cost |
| Screen capture | `mss` (<10ms) | Fastest Python screenshot |
| Multi-monitor | `screeninfo` + `pywin32` | Enumerate all displays |
| AI Brain | **Adapter pattern** (Claude/Gemini/OpenAI/Ollama) | Provider-agnostic, user picks |
| Default AI model | `claude-sonnet-5` (vision) | Best vision + reasoning |
| Click execution | `pyautogui` | Cross-app click automation |
| Overlay | PyQt6 (transparent, always-on-top) | True transparency, smooth animations |
| TTS (instant) | `pyttsx3` (Windows SAPI) | Zero latency, offline |
| TTS (quality) | ElevenLabs Turbo (streaming) | Natural voice, ~300ms first chunk |
| Raw memory | SQLite | Simple, local |
| Semantic memory | ChromaDB | Local vector DB |
| Wiki memory | **Obsidian vault** (Markdown files) | Human-readable, visual graph, editable |
| Orchestration | Python `asyncio` | Non-blocking concurrent pipeline |
| Packaging | PyInstaller | Single `.exe` |

---

## AI Usage Optimization

### Cost Tiers (per interaction)

| Path | Approximate cost | When triggered |
|---|---|---|
| Working memory hit | ~$0.000 | Repeat question in same session |
| UIA + Jev element picker | ~$0.0001 | Most click and screen commands |
| OmniParser + Jev element picker | ~$0.0002 | Apps without accessibility tree |
| Full Claude Vision | ~$0.008 | Complex reasoning, novel layouts |

### Strategies

1. **UIA first**: For any screen or click query, try the accessibility tree before touching the vision model — free for 90%+ of Windows-native apps
2. **Instructor for element selection**: Give the model a list of element names and ask it to pick one — 100× cheaper than sending a screenshot
3. **Screenshot compression**: 1280×720 JPEG 80% before sending to vision model (~4× token reduction)
4. **Crop to active window**: Never send full desktop to vision model
5. **Intent routing**: Haiku classifier costs ~0.01¢; this saves a ~1¢ Claude Vision call when no screenshot is needed
6. **Memory-first answers**: Vector similarity > 0.92 → answer from Obsidian wiki, no model call
7. **Streaming TTS**: Start speaking while model is still generating (ElevenLabs WebSocket)
8. **UI map caching**: Cache UIA element tree for 10 seconds per window — UI rarely changes between queries
9. **Parallel screen capture**: Start screenshot in background immediately after wake word — ready by the time classification finishes
10. **Token cap**: Max 2000 output tokens per response; Krithika guides step-by-step, not paragraphs

---

## Development Phases

### Phase 1 — Core Voice Pipeline (Week 1)
- [ ] Wake word (Porcupine) + audio capture (sounddevice + Silero VAD)
- [ ] Whisper STT integration (local)
- [ ] pyttsx3 TTS output
- [ ] Simple terminal echo loop: hear yourself back through Krithika

**Milestone**: Say "Hey Krithika, what time is it?" and hear the answer.

### Phase 2 — Intent Router + UIA Screen Reading (Week 1-2)
- [ ] TypeSafe SDK setup + Jev intent schema (Choice + Noul questions)
- [ ] Confidence-gated routing logic
- [ ] `pywinauto` UIA accessibility tree reader
- [ ] OmniParser integration (fallback)
- [ ] Basic screenshot capture with `mss`

**Milestone**: Say "Krithika, where is the Import button?" in DaVinci Resolve — get correct element name and coordinates without a vision call.

### Phase 3 — Visual Overlay (Week 2)
- [ ] PyQt6 transparent always-on-top window
- [ ] Pulsing highlight box at given coordinates
- [ ] Animated arrow system
- [ ] Krithika HUD panel (listening / thinking / speaking states)
- [ ] Multi-monitor detection and overlay per screen

**Milestone**: Say "Where is the Import button?" and see a pulsing box drawn around it.

### Phase 4 — AI Brain + Adapter Pattern (Week 2-3)
- [ ] `BrainAdapter` abstract interface
- [ ] `ClaudeAdapter` implementation (claude-sonnet-5, vision)
- [ ] `OllamaAdapter` implementation (local fallback)
- [ ] Config file for provider switching
- [ ] Full orchestrator async loop
- [ ] Click-on-command with `pyautogui`

**Milestone**: Complete a full guided workflow in DaVinci Resolve using only voice.

### Phase 5 — Memory System (Week 3)
- [ ] SQLite history logging
- [ ] ChromaDB vector store
- [ ] Obsidian vault writer (auto-generate wiki pages after task completion)
- [ ] Memory retrieval injection into AI Brain context
- [ ] Task tracking (Active.md + Completed/)

**Milestone**: Complete a task, restart Krithika, ask what you did last time — Krithika recalls from Obsidian.

### Phase 6 — Polish & Voice (Week 4)
- [ ] ElevenLabs streaming TTS
- [ ] Custom voice setup (user provides audio sample)
- [ ] App-specific system prompts (Resolve, Photoshop, Office, etc.)
- [ ] Error handling + retry logic
- [ ] "Stop" / "Cancel" voice command
- [ ] PyInstaller packaging into single `.exe`

**Milestone**: Fully hands-free demo. Zero keyboard or mouse. Custom Krithika voice.

---

## System Requirements

| Requirement | Your Machine | Status |
|---|---|---|
| OS | Windows 11 Enterprise | ✅ |
| Processor | Intel Core Ultra 5 235H | ✅ (Whisper small ~1.5s on CPU) |
| RAM | 32 GB | ✅ (~2.5GB total: Whisper + OmniParser + PyQt6 + ChromaDB) |
| GPU | Intel Arc (integrated) | ✅ (Whisper can use DirectML acceleration → ~0.5s) |
| Internet | Claude API + ElevenLabs | Required for cloud TTS/brain |
| Microphone | USB or 3.5mm | Required (not built into machine) |
| Obsidian | Free desktop app | Optional (for visual wiki browsing) |

---

## Project Folder Structure

```
krithika/
├── core/
│   ├── voice_input.py         # Wake word + Whisper STT
│   ├── intent_router.py       # Instructor + Pydantic classifier
│   ├── screen_reader.py       # UIA + OmniParser + mss
│   ├── tts_output.py          # pyttsx3 + ElevenLabs
│   ├── clicker.py             # pyautogui click executor
│   └── orchestrator.py        # Main asyncio loop
├── brain/
│   ├── adapter.py             # BrainAdapter abstract base
│   ├── claude_adapter.py      # Anthropic implementation
│   ├── gemini_adapter.py      # Google implementation
│   ├── openai_adapter.py      # OpenAI implementation
│   └── ollama_adapter.py      # Local Ollama implementation
├── overlay/
│   ├── main_window.py         # PyQt6 transparent overlay
│   ├── highlight.py           # Boxes + arrows
│   └── hud_panel.py           # Krithika status panel
├── memory/
│   ├── history.py             # SQLite raw log
│   ├── vectors.py             # ChromaDB semantic search
│   ├── obsidian_writer.py     # Write wiki to Obsidian vault
│   └── working_memory.py      # Session state dict
├── prompts/
│   ├── system_base.txt        # Base Krithika personality
│   ├── davinci_resolve.txt    # App-specific prompt
│   ├── photoshop.txt
│   └── windows_settings.txt
├── data/
│   ├── history.db
│   └── vectors/               # ChromaDB store
# Obsidian vault lives at %USERPROFILE%\KrithikaMemory\ — outside the project
├── config.yaml                # Provider, model, API keys config
├── main.py                    # Entry point
└── requirements.txt
```

---

## Open Questions (Confirm Before Building)

1. **Gemini / other providers**: Do you have API keys for any other provider (Gemini, OpenAI) to test the adapter pattern during development, or should we start Claude-only and add adapters in Phase 4?

3. **Obsidian**: Should Krithika also *read* from the Obsidian vault (using the Local REST API plugin), or is writing enough for now? Reading enables richer memory retrieval via backlinks.

4. **Custom voice (Phase 6)**: When we reach Phase 6, you'll need to provide a ~5-minute audio sample of the voice you want (your own voice, a character, etc.). ElevenLabs Voice Cloning requires this. Have it ready for Phase 6.


---

*Plan v2 authored: 2026-09-30. Previous file: JARVIS_PLAN.md (deprecated — use this file).*
