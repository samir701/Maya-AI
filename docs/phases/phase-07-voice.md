# Phase 07 — Real-Time Voice & Audio Subsystem

## Overview

Phase 07 implements a modular, secure, and extensible **Real-Time Voice & Audio Subsystem** for ZETTA AI Employee / Maya AI. This layer provides full audio input/capture, Voice Activity Detection (VAD), Speech-to-Text (STT) transcription, Text-to-Speech (TTS) synthesis, and interactive conversational voice session management.

Spoken natural language commands seamlessly integrate with `InteractionManager`, `ToolRouter`, and `ToolRegistry`, while strictly adhering to `SecurityManager` permission gates, confirmation policies, and privacy standards.

---

## Architectural Flow

```
+-----------------------------------------------------------------------------------+
|                                  USER / ENVIRONMENT                               |
|              (Microphone / Audio In)               (Speaker / Audio Out)          |
+-----------------------------------------------------------------------------------+
                               |                                  ^
                               v                                  |
               +-------------------------------+  +-------------------------------+
               |     AudioCaptureProvider      |  |     AudioPlaybackProvider     |
               |  (LinuxALSA / FakeCapture)    |  |   (LinuxALSA / FakePlayback)  |
               +-------------------------------+  +-------------------------------+
                               |                                  ^
                        Raw PCM Chunks                     Audio Stream / WAV
                               v                                  |
               +-------------------------------+  +-------------------------------+
               |    Voice Activity Detector    |  |          TTSProvider          |
               |     (EnergyVAD / FakeVAD)     |  |     (LocalTTS / FakeTTS)      |
               +-------------------------------+  +-------------------------------+
                               |                                  ^
                          Speech Segments                 Assistant Response
                               v                                  |
               +-------------------------------+                  |
               |          STTProvider          |                  |
               |     (LocalSTT / FakeSTT)      |                  |
               +-------------------------------+                  |
                               |                                  |
                        Transcribed Text                          |
                               v                                  |
+-----------------------------------------------------------------------------------+
|                                  VoiceController                                  |
|   State Machine: IDLE <-> LISTENING <-> PROCESSING <-> SPEAKING <-> ERROR         |
|   Coordinates turns, audio buffers, timeouts, cancellation, and echo prevention   |
+-----------------------------------------------------------------------------------+
                               |                                  ^
                      Transcribed Prompt                 Response Text
                               v                                  |
+-----------------------------------------------------------------------------------+
|                                InteractionManager                                 |
|            - Session Management (SessionManager)                                  |
|            - Event Publishing (EventBus: VOICE_*, USER_*, ASSISTANT_*)            |
|            - Memory Retrieval & Injection (ContextBuilder + MemoryManager)        |
|            - Spoken Tool Routing:                                                 |
|                   ToolRouter -> ToolRegistry -> SecurityManager                   |
|                   (Strict Permission Checks & User Confirmation Gating)           |
|            - AI Core Generation (AIBrain -> OpenAI / Local / Fake Provider)       |
+-----------------------------------------------------------------------------------+
```

---

## Directory Structure

```
core/zetta/voice/
├── __init__.py                     # Public exports (VoiceManager, VoiceSession, AudioData, etc.)
├── models/                         # Data models
│   ├── __init__.py
│   ├── audio.py                    # AudioFormat, AudioChunk, AudioData, AudioDevice
│   ├── session.py                  # VoiceSession, VoiceSessionState, VoiceTurn
│   ├── stt.py                      # TranscriptionResult, TranscriptionSegment
│   ├── tts.py                      # SynthesisRequest, SynthesisResult, VoiceProfile
│   └── vad.py                      # VADResult, SpeechActivityState
├── audio/                          # Audio capture & playback abstractions
│   ├── __init__.py
│   ├── base.py                     # AudioCaptureProvider, AudioPlaybackProvider (ABC)
│   ├── fake.py                     # FakeAudioCaptureProvider, FakeAudioPlaybackProvider
│   ├── linux.py                    # LinuxALSAAudioCaptureProvider, LinuxAudioPlaybackProvider
│   └── device.py                   # AudioDeviceManager (ALSA / pactl device discovery)
├── speech_to_text/                 # STT Providers
│   ├── __init__.py
│   ├── base.py                     # STTProvider (ABC)
│   ├── fake.py                     # FakeSTTProvider (deterministic keyword & intent mapping)
│   └── local.py                    # LocalSTTProvider (configurable whisper / ffmpeg / CLI / HTTP)
├── text_to_speech/                 # TTS Providers
│   ├── __init__.py
│   ├── base.py                     # TTSProvider (ABC)
│   ├── fake.py                     # FakeTTSProvider (deterministic PCM/WAV sine tone generator)
│   └── local.py                    # LocalTTSProvider (configurable espeak-ng / aplay / HTTP)
├── vad/                            # Voice Activity Detection
│   ├── __init__.py
│   ├── detector.py                 # EnergyVADDetector (zero-dep pure-Python RMS energy VAD)
│   └── fake.py                     # FakeVADDetector (deterministic scripted speech frames)
├── controller.py                   # VoiceController (turn coordination, stream orchestration)
└── manager.py                      # VoiceManager facade (singleton, lifecycle, capabilities)

core/zetta/tools/voice/             # ToolRegistry Voice Tools
├── __init__.py
└── voice_tools.py                  # VoiceStatusTool, VoiceCaptureTool, VoiceTranscribeTool,
                                    # VoiceSynthesizeTool, VoiceSessionTool
```

---

## Components Implemented

### 1. Audio Capture & Playback
- **`AudioCaptureProvider` / `AudioPlaybackProvider`**: Base abstractions for hardware and virtual devices.
- **`LinuxALSAAudioCaptureProvider`**: Uses standard Linux `arecord` subprocess streaming 16kHz mono `pcm_s16le` audio.
- **`LinuxAudioPlaybackProvider`**: Uses standard Linux `aplay` or `paplay` for low-latency audio playback.
- **`AudioDeviceManager`**: Discovers system input/output cards and devices via `arecord -l` and `aplay -l`.
- **`FakeAudioCaptureProvider` / `FakeAudioPlaybackProvider`**: 100% deterministic in-memory providers generating synthetic sinusoidal PCM chunks with zero external hardware or network dependencies.

### 2. Zero-Dependency Voice Activity Detection (VAD)
- **`EnergyVADDetector`**: Pure Python Root-Mean-Square (RMS) amplitude calculation over 16-bit signed PCM samples (`struct.unpack("<h", ...)`).
- **State Machine**: Evaluates speech onset thresholds and silence hangover buffers to determine speech boundaries without speech-to-text latency.
- **`FakeVADDetector`**: Deterministic VAD simulator for scripted unit testing.

### 3. Speech-to-Text (STT) & Text-to-Speech (TTS)
- **`STTProvider`**: Base interface returning structured `TranscriptionResult`.
- **`FakeSTTProvider`**: Deterministic keyword and prompt mapping with queued custom responses.
- **`LocalSTTProvider`**: Configurable local whisper binary or HTTP REST transcription.
- **`TTSProvider`**: Base interface returning `SynthesisResult` with `AudioData`.
- **`FakeTTSProvider`**: Generates valid standard WAV container headers and audio tones using Python's standard library `wave` and `struct`.
- **`LocalTTSProvider`**: Synthesizes speech using `espeak-ng`, `espeak`, `flite`, or HTTP endpoints.

### 4. Voice Controller & Voice Manager
- **`VoiceController`**: Coordinates turn lifecycle (`IDLE` ⇄ `LISTENING` ⇄ `PROCESSING` ⇄ `SPEAKING` ⇄ `ERROR`), manages audio buffering, cancels active turns on demand, and prevents acoustic feedback loops (microphones are paused during speech output).
- **`VoiceManager`**: High-level singleton facade providing `status()`, `capabilities()`, `record_clip()`, `play_audio()`, `transcribe()`, `synthesize()`, `speak()`, `start_session()`, and `execute_turn()`.

### 5. Tool Integration (5 Voice Tools)
Registered in `ToolRegistry` and exposed through `ToolRouter`:

| Tool Name | Category | Permission | Confirmation | Description |
| :--- | :---: | :---: | :---: | :--- |
| `voice_status` | voice | `LOW` | No | Inspect audio devices, capture/playback status, and STT/TTS readiness |
| `voice_capture` | voice | `LOW` | No | Record an ephemeral test audio sample from microphone |
| `voice_transcribe` | voice | `LOW` | No | Transcribe audio into text using configured STT provider |
| `voice_synthesize` | voice | `LOW` | No | Synthesize text into speech audio and optionally play through speaker |
| `voice_session` | voice | `MEDIUM` | No | Start, execute conversational turn, or stop an interactive voice session |

---

## Security & Privacy Guardrails

1. **Strict Permission & Confirmation Enforcement**:
   Spoken commands invoke `InteractionManager` and `ToolRouter`, executing through `ToolRegistry.execute()`. High-risk tools (e.g. `file_delete`, `terminal_execute`) **strictly require user confirmation and appropriate permission levels**. Spoken commands cannot bypass security gates.
2. **Zero Raw Audio Persistence**:
   Microphone audio is processed entirely in memory buffers and is **never persisted to disk** unless explicitly configured (`ZETTA_VOICE_PERSIST_AUDIO=true`).
3. **Data Model Privacy**:
   `AudioData.to_dict()` strictly omits raw binary audio bytes, exposing only duration, sample rate, channels, and RMS energy metadata.
4. **Secret Masking**:
   Transcripts containing credentials, tokens, or passwords are automatically sanitized through `SecurityManager`.
5. **No Uncontrolled Autonomous Execution**:
   No background clicker, autonomous desktop typing loop, or uncontrolled computer control is introduced.

---

## CLI Commands

Unified under `core/zetta/cli.py` and `cli.py`:

```bash
# Show status and hardware devices
python3 cli.py voice status [--fake]
python3 cli.py voice devices [--fake]

# Test input and output
python3 cli.py voice test-input [--duration 3.0] [--fake]
python3 cli.py voice test-output [--fake]

# Speech recognition and synthesis
python3 cli.py voice stt sample.wav [--fake]
python3 cli.py voice tts "Hello from ZETTA" [--play] [--fake]

# Interactive voice turns and continuous sessions
python3 cli.py voice listen [--duration 5.0] [--fake]
python3 cli.py voice turn [--fake]
python3 cli.py voice session [--fake]
```

---

## Test Verification

- **Unit Tests**: 23 tests in `tests/unit/test_phase07_voice.py` covering models, VAD, fake providers, Linux providers, controller state machine, manager facade, tool registry, and tool routing.
- **Integration Tests**: 5 tests in `tests/integration/test_phase07_integration.py` covering end-to-end spoken tool execution, security confirmation enforcement, AI conversation, multi-turn voice sessions, and health-check integration.
- **Total Test Suite**: 249 passed (221 baseline + 28 Phase 07 tests), 0 failures.
- **Audit Verification**: `./run_all.sh` passed 100%.
