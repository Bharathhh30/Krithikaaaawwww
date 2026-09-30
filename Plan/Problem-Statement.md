# Krithika — Problem Statement

---

## The Problem

**Every powerful piece of software on your computer requires you to already know how to use it.**

When someone opens DaVinci Resolve for the first time, they see hundreds of panels, buttons, and menus — with no idea where to start. They pause their work, open YouTube, watch a 20-minute tutorial, pause the video, switch back to the app, forget what they watched, and repeat. This cycle kills momentum, wastes hours, and shuts people out of tools that could genuinely help them.

This problem is not limited to beginners. Even experienced users constantly switch between a browser tab and their active application — looking up shortcuts, searching for features, reading documentation — all while their hands stay glued to a keyboard and mouse they can't put down.

---

## Who Is Affected

| User Group | Pain Point |
|---|---|
| **Beginners learning new software** | No idea where anything is. Tutorials are disconnected from the actual screen they're looking at. |
| **Knowledge workers switching tools** | Productive in one app, lost in another. Cost of learning new software is too high. |
| **People with physical disabilities** | Keyboard and mouse interaction is a barrier. Existing voice tools (Cortana, Siri) don't understand the screen context. |
| **Non-English speakers** | Documentation and tutorials exist primarily in English. A voice companion that understands their language removes this barrier. |
| **Professionals under time pressure** | No time to search and read. Need the answer on-screen, right now. |

---

## Why Existing Solutions Fail

| Solution | Why It Falls Short |
|---|---|
| **YouTube tutorials** | Split-screen attention. Pausing, rewinding, and re-watching breaks workflow entirely. Static — they don't know what's on *your* screen. |
| **Product documentation** | Written for general cases, not your specific situation. Requires reading, switching context, and translating text into action. |
| **Cortana / Siri / Google Assistant** | General-purpose. They cannot see your screen, don't know which software is open, and can't point to a button. |
| **Copilot in Windows** | Requires keyboard interaction. Text-based. Doesn't visually guide on-screen. Limited to Microsoft products. |
| **Accessibility tools (screen readers)** | Built for people with vision impairments. They read the screen out loud but don't guide *action*. |

None of the above can answer: *"I'm in this exact app, looking at this exact screen — what do I click right now?"*

---

## The Solution — Krithika

**Krithika is a voice-operated AI partner that lives on your screen, sees what you see, and guides you through anything — without ever touching the keyboard or mouse.**

You speak. Krithika listens, looks at your screen, identifies exactly where the button or menu is, draws a glowing arrow pointing at it, and tells you what to do next. Step by step. In any software. With memory of everything you've done before.

---

## How It Works

```
You speak           →   "Hey Krithika, how do I import footage into DaVinci Resolve?"

Krithika sees       →   Takes a screenshot of your current screen, reads the UI elements

Krithika guides     →   Draws a pulsing highlight box on "Import Media" in the Media Pool panel
                        Speaks: "Click the Import Media button in the bottom-left panel"

You click           →   Or say "Krithika, click Import Media" and it clicks for you

Krithika remembers  →   Writes a wiki page to your Obsidian vault:
                        "How to Import Media in DaVinci Resolve"
```

---

## Key Innovations

### 1. Full computer control by voice

Krithika doesn't just point and explain — it *does*. You can tell it to open applications, type text, press keys, use keyboard shortcuts, scroll, switch windows, and chain all of these into multi-step sequences in a single command. *"Open terminal, type claude, press Enter"* — Krithika does all three in sequence, immediately, with no confirmation step needed. The voice command is the confirmation.

This means the keyboard and mouse are truly optional — not just for simple clicks, but for entire workflows.

### 2. Vision-first screen understanding
Krithika doesn't just hear you — it sees exactly what's on your screen and maps its answer to the real coordinates of the real buttons in front of you. No generic instructions. Everything is specific to your screen, your app, your state.

### 3. Fully hands-free
The entire interaction is voice. No keyboard. No mouse. From wake word to "task complete", your hands are free. This makes powerful software accessible to anyone who can speak — regardless of technical skill or physical ability.

### 4. Persistent memory
Krithika remembers every session. It builds a personal wiki in Obsidian of everything you've learned, organised by application and task. The more you use it, the smarter it gets — about *you*.

### 5. Intelligent cost routing
Rather than sending every query to an expensive AI vision model, Krithika first reads the Windows accessibility tree (free), then uses TypeSafe's Jev model for typed classification (cheap), and only escalates to a full vision call when truly needed. This makes real-time guidance economically viable.

### 6. Provider-agnostic AI brain
Krithika uses an adapter pattern — users can plug in their existing API key (Claude, Gemini, OpenAI, or a local Ollama model). No vendor lock-in.

---

## Technical Stack Summary

| Layer | Technology |
|---|---|
| Voice Input | Picovoice Porcupine (wake word) + OpenAI Whisper (local STT) |
| Intent Classification | TypeSafe Jev — typed AI judgments, not text generation |
| Screen Reading | Windows UI Automation → OmniParser → Claude Vision (tiered) |
| AI Brain | Claude claude-sonnet-5 via adapter pattern (swappable) |
| Visual Guidance | PyQt6 transparent always-on-top overlay |
| Voice Output | ElevenLabs Turbo streaming TTS (custom voice) |
| Memory | SQLite + ChromaDB + Obsidian vault at `~/KrithikaMemory/` |
| Platform | Windows 11, distributed as a single `.exe` |

---

## The "JARVIS" Moment

The vision is not a chatbot. It is not a search engine. It is a **partner** — one that knows your workflows, remembers your history, understands the software you use, and is always on, always watching, always ready to help.

The closest cultural reference is Tony Stark's JARVIS: an AI that is not a tool you reach for, but a presence that is already there, already paying attention, already three steps ahead.

Krithika is that for everyone — not just fictional billionaires.

---

## Impact

**Short term**: Any person can learn any software, guided step-by-step, without watching a single tutorial or reading a single documentation page.

**Medium term**: Professionals stop losing hours to tool-switching and context-switching. Creative output accelerates. The learning curve for powerful software collapses.

**Long term**: The keyboard and mouse are no longer the gatekeepers of computing. Anyone who can speak can use any tool.

---

## Competitive Differentiation

| Feature | Krithika | Copilot | Siri / Cortana | Screen readers |
|---|---|---|---|---|
| Sees your screen | ✅ | Partial | ❌ | ✅ |
| Points to exact UI elements | ✅ | ❌ | ❌ | ❌ |
| Fully voice-operated | ✅ | ❌ | ✅ | ✅ |
| Works in any software | ✅ | ❌ | ❌ | Partial |
| Persistent memory | ✅ | ❌ | ❌ | ❌ |
| Clicks on command | ✅ | ❌ | ❌ | ❌ |
| Provider-agnostic AI | ✅ | ❌ | ❌ | ❌ |
| Offline capable | Partial | ❌ | ❌ | ✅ |

---

## Open Questions / Future Directions

- **Privacy**: Currently screenshots are sent to cloud AI. A future local-only mode using on-device vision models (Ollama + LLaVA) would make Krithika fully private.
- **Mobile**: Extending to Android/iOS would require a different accessibility API but the core concept holds.
- **Multi-language**: Whisper already supports 90+ languages. The TTS and AI Brain need to match.
- **Proactive guidance**: Instead of waiting for a question, Krithika could detect when a user is stuck (hovering, inactivity, confused navigation) and offer help unprompted.

---

*Krithika — your screen. your voice. your partner.*
