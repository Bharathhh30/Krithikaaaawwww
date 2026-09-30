# Phase 1 — Voice Input Pipeline

## Overview

Build the always-on listening backbone. After this phase, Krithika wakes up on a keyword, records the user's speech, transcribes it, and speaks a response — entirely without keyboard or mouse. This is the foundation every other phase builds on.

---

## What We're Building

| Component | Purpose |
|---|---|
| Wake word detector | Always-on background listener; triggers on "Hey Krithika" |
| Audio recorder | Captures mic input after wake word; stops automatically on silence |
| Voice Activity Detection (VAD) | Detects when the user has finished speaking |
| Speech-to-Text (STT) | Converts recorded audio to text using local Whisper |
| Local TTS | Speaks responses instantly using Windows SAPI |
| Terminal test loop | End-to-end test: hear yourself echoed back through Krithika |

---

## Files to Create

```
krithika/
└── voice/
    ├── __init__.py
    ├── wake_word.py        # Porcupine wake word listener
    ├── recorder.py         # sounddevice capture + Silero VAD
    └── transcriber.py      # OpenAI Whisper STT

krithika/
└── tts/
    ├── __init__.py
    ├── base.py             # TTSProvider ABC
    ├── sapi_tts.py         # Windows SAPI via pyttsx3 (instant, offline)
    └── elevenlabs_tts.py   # Stub — implemented in Phase 6

tests/unit/
├── test_recorder.py
└── test_transcriber.py
```

---

## Implementation Details

### `wake_word.py` — WakeWordDetector

```python
class WakeWordDetector:
    def __init__(self, access_key: str, keyword: str = "krithika") -> None: ...
    async def wait_for_wake_word(self) -> None:
        """Blocks until wake word is detected. Runs Porcupine in a thread pool."""
    def stop(self) -> None: ...
```

- Use `pvporcupine` Python SDK
- The keyword "krithika" must be a custom keyword file created via Picovoice Console (free tier)
- Run in a `ThreadPoolExecutor` to keep the asyncio loop unblocked
- CPU usage must stay below 2% — Porcupine guarantees this

### `recorder.py` — AudioRecorder

```python
class AudioRecorder:
    async def record_until_silence(self, silence_duration_s: float = 1.5) -> bytes:
        """Records from mic until silence_duration_s seconds of silence. Returns WAV bytes."""
```

- Use `sounddevice` for mic capture (16kHz, mono, int16)
- Use `silero-vad` (via `torch`) to detect speech vs silence frame by frame
- Stop recording when VAD detects `silence_duration_s` seconds of continuous silence
- Return raw WAV bytes in memory — no temp files

### `transcriber.py` — WhisperTranscriber

```python
class WhisperTranscriber:
    def __init__(self, model_size: str = "small") -> None: ...
    async def transcribe(self, audio_bytes: bytes) -> str:
        """Returns transcribed text. Runs Whisper in a thread pool."""
```

- Load Whisper model once at init (not per call)
- `whisper-small` default; configurable via `config.yaml`
- Accelerate with DirectML on Intel Arc: `whisper.load_model("small", device="directml")` if available, fall back to CPU
- Run inference in `ThreadPoolExecutor` — never block the event loop

### `tts/base.py` — TTSProvider ABC

```python
from abc import ABC, abstractmethod

class TTSProvider(ABC):
    @abstractmethod
    async def speak(self, text: str) -> None:
        """Speak the given text. Must not block the event loop."""
```

### `sapi_tts.py` — SAPITTSProvider

- Use `pyttsx3`, run in `ThreadPoolExecutor`
- Instant, zero latency, fully offline
- Used for acknowledgments: "Got it", "Looking at your screen", "Thinking..."

### `elevenlabs_tts.py` — ElevenLabsTTSProvider (stub)

- Implement the ABC but raise `NotImplementedError` with message "ElevenLabs TTS is implemented in Phase 6"
- This lets the orchestrator reference it without breaking

---

## Dependencies to Add to `requirements.txt`

```
pvporcupine>=3.0.0
sounddevice>=0.4.6
openai-whisper>=20231117
silero-vad>=5.1
torch>=2.1.0          # required by silero-vad; CPU-only build is fine
pyttsx3>=2.90
```

---

## Testing Requirements

### Unit Tests — `tests/unit/test_recorder.py`
- Test that silence detection terminates recording after the configured duration
- Mock `sounddevice` and Silero VAD — do not require a real microphone
- Test that returned audio is valid WAV bytes

### Unit Tests — `tests/unit/test_transcriber.py`
- Test that `WhisperTranscriber.transcribe()` returns a non-empty string for a known audio fixture
- Include a short WAV fixture file (`tests/fixtures/hello.wav`) with the word "hello"
- Mock the Whisper model in CI (loading 145MB model in CI is too slow) — use `unittest.mock.patch`

### Manual Smoke Test
```
python -c "
import asyncio
from krithika.voice.transcriber import WhisperTranscriber
t = WhisperTranscriber()
# Speak into mic for 3 seconds then go silent
result = asyncio.run(t.transcribe_from_mic())  
print(result)
"
```

---

## Running Locally

After this phase, the terminal test loop in `main.py` should work:

```
python main.py
```

Expected behaviour:
1. Terminal prints: `Krithika is ready. Say "Hey Krithika" to begin.`
2. User says "Hey Krithika, what's two plus two?"
3. Terminal prints the transcribed text
4. Krithika speaks the text back (echo mode for now)

---

## Definition of Done

- Wake word triggers reliably within 1 second of speaking "Hey Krithika"
- Audio recording stops automatically 1.5 seconds after the user stops speaking
- Whisper transcribes speech to text with no more than 2 seconds latency on the target machine
- `pyttsx3` TTS speaks a response back
- All unit tests pass in CI
- No blocking calls in the asyncio event loop (verified by running with `asyncio.get_event_loop().set_debug(True)`)

---

## Success Criteria

1. Say "Hey Krithika, tell me something" → Krithika wakes, records, transcribes, and echoes the transcription back via TTS
2. Whisper latency ≤ 2 seconds on Intel Core Ultra 5 235H (CPU mode)
3. Wake word false positive rate: less than 1 per 10 minutes of background noise
4. `pytest tests/unit/` passes in CI with zero failures

---

## Checklist

- [ ] `pvporcupine` custom keyword file created for "krithika" (via Picovoice Console)
- [ ] `wake_word.py` — `WakeWordDetector` implemented and tested
- [ ] `recorder.py` — `AudioRecorder` with Silero VAD implemented
- [ ] `transcriber.py` — `WhisperTranscriber` with DirectML fallback implemented
- [ ] `tts/base.py` — `TTSProvider` ABC defined
- [ ] `tts/sapi_tts.py` — `SAPITTSProvider` implemented
- [ ] `tts/elevenlabs_tts.py` — stub with `NotImplementedError`
- [ ] `tests/fixtures/hello.wav` added
- [ ] Unit tests written and passing
- [ ] Terminal echo loop working end-to-end
- [ ] CI pipeline passes

---

## Conclusion

> *To be filled after completion.*
> Document latency measured on the actual machine, any issues with Porcupine keyword file creation, DirectML availability, and anything Phase 2 needs to know.
