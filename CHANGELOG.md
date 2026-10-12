# Changelog

All notable changes to the ZETTA AI Employee project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.0] - Phase 08 Autonomous Agents & AI Employee (2026-09-11)
### Added
- **Agent Framework & Core Abstractions**:
  - `BaseAgent` class with explicit lifecycle states (`CREATED`, `READY`, `RUNNING`, `WAITING`, `COMPLETED`, `FAILED`, `CANCELLED`, `PAUSED`).
  - `AgentRegistry` and `AgentManager` with thread-safe registration and lifecycle tracking.
  - `AgentContext`, `AgentResult`, `AgentError` models.
- **Autonomous Planner & Task Graph**:
  - `TaskGraph` Directed Acyclic Graph (DAG) manager with Kahn's algorithm topological sorting and cycle detection.
  - `AutonomousPlanner` decomposing user goals into multi-stage executable plans with tool and agent assignments.
- **Agent Orchestrator & Concurrency Engine**:
  - `AgentOrchestrator` coordinating parallel stage execution, retry policies, subtask timeouts, cancellation propagation, and outcome verification.
  - `BackgroundAgentRunner` for non-blocking long-running background tasks.
  - `UnifiedAutonomousWorkflow` binding Planner, Agent Fleet, Tools, Verification, and Episodic Memory Consolidation into an end-to-end employee pipeline.
- **Specialized Agent Fleet**:
  - `GeneralAssistantAgent`, `BrowserAgent`, `VisionAgent`, `VoiceAgent`, `ResearchAgent`, `DocumentAgent`.
  - `CodingAgent`: workspace boundary enforcement, code inspection, automated editing, test execution, and autonomous self-repair loop.
  - `HermesAutonomousAgent`: long-running autonomous execution with checkpoint persistence and state recovery.
- **Accessibility & Unified Computer Agent**:
  - 25 composable accessibility capabilities for OS element inspection, mouse/keyboard automation, and window control.
  - `AccessibilityManager` and `AccessibilityAgent`.
  - `UnifiedComputerAgent` uniting Desktop, Applications, Filesystem, Terminal, Clipboard, Vision, Browser, and Accessibility.
- **Personas, Skills, Plugins & Workflows**:
  - `PersonaManager` with `DEFAULT`, `PROFESSIONAL`, and `CREATIVE` personas.
  - Extensible, validated, permission-gated `SkillManager` and `SkillRegistry`.
  - Lifecycle-managed `PluginManager` and `PluginRegistry`.
  - Reusable macro and declarative workflow engine (`WorkflowEngine`).
- **External Integration Architectures**:
  - Desktop ↔ Mobile Phone Link protocol (`PhoneManager`, `PhoneProvider`, `FakePhoneProvider`).
  - `VoiceGuardian` security gate classifying speakers (`AUTHORIZED`, `UNKNOWN`, `RESTRICTED`).
  - Communication suite: Email, WhatsApp-style messaging, and expense reporting providers with user confirmation gating.
  - Creator suite: multi-platform title, description, and tag generation (`CreatorManager`).
- **CLI & Health System**:
  - Added CLI subcommands: `agent`, `plan`, `skill`, `persona`, `workflow`, `bgjob`, `phone`.
  - Added Check 14 to system health checker (`phase08_autonomous_agents`).
- **Test Suite**:
  - 11 unit test suites and master integration test suite covering all Phase 08 capabilities.
  - Full suite: 368 passing tests, 0 failures, 0 errors.

## [0.7.0] - Phase 07 Real-Time Voice & Audio Subsystem (2026-09-09)
### Added
- **Audio Capture & Playback Abstraction**:
  - `AudioCaptureProvider` and `AudioPlaybackProvider` abstract base classes.
  - `LinuxALSAAudioCaptureProvider` utilizing standard Linux `arecord` subprocess streaming 16kHz mono `pcm_s16le` audio.
  - `LinuxAudioPlaybackProvider` utilizing standard Linux `aplay` or `paplay` for local playback.
  - `AudioDeviceManager` discovering hardware and virtual audio devices via `arecord -l` and `aplay -l`.
  - `FakeAudioCaptureProvider` and `FakeAudioPlaybackProvider` for 100% deterministic offline in-memory audio simulation.
- **Zero-Dependency Voice Activity Detection (VAD)**:
  - `EnergyVADDetector` calculating Root-Mean-Square (RMS) amplitude over 16-bit PCM chunks (`struct.unpack`) in pure Python without external C libraries.
  - Speech onset, active speech tracking, and silence hangover buffers to determine speech boundaries reliably.
  - `FakeVADDetector` for deterministic scripted speech frame simulation.
- **Speech-to-Text (STT) & Text-to-Speech (TTS) Providers**:
  - `STTProvider` and `TTSProvider` base interfaces.
  - `FakeSTTProvider` and `FakeTTSProvider` generating standard WAV/PCM audio headers and tones using Python's `wave` and `struct` standard libraries.
  - `LocalSTTProvider` and `LocalTTSProvider` supporting local whisper, `espeak-ng`, `aplay`, or external HTTP endpoints.
- **Voice Controller & Voice Manager**:
  - `VoiceController` state machine (`IDLE` ⇄ `LISTENING` ⇄ `PROCESSING` ⇄ `SPEAKING` ⇄ `ERROR`) with echo prevention (pausing microphone listening during speech output) and turn cancellation.
  - `VoiceManager` facade with singleton access (`get_voice_manager()`), device inspection, status, capabilities, and session turn coordination.
- **Tool System Integration**:
  - 5 Voice Tools registered in `ToolRegistry`: `voice_status`, `voice_capture`, `voice_transcribe`, `voice_synthesize`, and `voice_session`.
  - Natural language intent routing in `ToolRouter` for spoken commands ("voice status", "say ...", "speak ...", "transcribe audio", etc.).
  - Security integration ensuring spoken commands invoke `ToolRegistry.execute()` and strictly enforce `SecurityManager` permissions and user confirmation policies.
- **Privacy Controls**:
  - Zero raw microphone audio persistence by default.
  - `AudioData.to_dict()` strictly redacts raw binary audio bytes.
  - Sensitive transcripts and credentials sanitized through `SecurityManager`.
- **Configuration & CLI**:
  - `VoiceSettings` dataclass added to `core/zetta/config/settings/settings.py` and `.env.example`.
  - Unified CLI command suite in `cli.py`: `voice status`, `voice devices`, `voice test-input`, `voice test-output`, `voice stt`, `voice tts`, `voice listen`, `voice turn`, and `voice session`.
- **Health Check & Import Resolution**:
  - Added Check 13 in `core/zetta/health.py` validating voice subsystem readiness and hardware availability.
  - Added 27 voice modules to `scripts/development/check_imports.py` (127/127 passed).
- **Test Suite**:
  - Added 23 unit tests in `tests/unit/test_phase07_voice.py` and 5 integration tests in `tests/integration/test_phase07_integration.py`.
  - Full project test suite: 249/249 tests passing (100% passed across Phases 00 through 07).

## [0.6.1] - Phase 06 CDP Navigation Lifecycle & Stale Target Hardening (2026-09-09)
### Fixed
- **CDP History Navigation Context Invalidation**: Replaced `Runtime.evaluate("window.history.back()")` with native DevTools protocol navigation (`Page.getNavigationHistory` + `Page.navigateToHistoryEntry` and `Page.reload`), preventing execution context destruction and `-32000: Inspected target navigated or closed` errors during top-level document frame unloads.
- **Dynamic CDP Target Reconnection**: Added auto-reconnect logic in `CDPClient.send_command` that detects disconnected sockets or navigated target notifications, rediscovers the active page target from `/json/list`, and retries the command once before erroring.
- **Target Affinity & Settling**: Implemented target affinity in `discover_page_target()` and document readiness polling (`document.readyState`) in `_wait_for_settle()`.
- **Target Refresh & Screenshot Accuracy**: Updated `LocalBrowserProvider.get_page_info()`, `history_action()`, and `capture_page_screenshot()` to force target refresh and eliminate synthetic `about:blank` fallbacks, ensuring screenshots accurately reflect the settled page.
- **CLI Persistence & Session Targeting**: Added root `cli.py` launcher, validated multi-process persistence across distinct CLI invocations, and ensured `--session` / `--session-id` explicit targeting remains isolated.
- **Regression Test Coverage**: Added 7 comprehensive regression tests in `TestLocalBrowserCDPNavigationLifecycle`, bringing test suite total to 221 passing tests (47 unit tests, 4 integration tests).

## [0.6.0] - Phase 06 Browser & Web Control Subsystem (2026-09-08)
### Added
- **Browser Models**: Structured dataclasses for `BrowserSession`, `BrowserTab`, `PageInfo`, `WebElement`, `ElementType`, `ElementLocation`, `ActionResult`, `ScrollDirection`, `HistoryAction`.
- **Browser Provider Abstraction**:
  - `BrowserProvider` base interface.
  - `FakeBrowserProvider`: 100% deterministic, zero-network in-memory browser simulation for offline tests and validation.
  - `LocalBrowserProvider`: System browser discovery (`google-chrome`, `chromium`, `firefox`), isolated user data directories, headless DOM dump parsing (`SimpleHTMLDOMParser`), and process cleanup.
- **Browser Controller**: `BrowserController` orchestrating session lifecycles, URL security validation (blocking `javascript:`, `vbscript:`, and path traversal outside sandbox), and credential masking for sensitive fields (`password`, `token`, etc.).
- **Browser Manager**: `BrowserManager` facade with singleton access (`get_browser_manager()`) and screenshot export into `<project_root>/runtime/captures/`.
- **12 Browser Tools**: `browser_status`, `browser_launch`, `browser_close`, `browser_navigate`, `browser_get_page`, `browser_detect_elements`, `browser_click`, `browser_type`, `browser_keyboard`, `browser_scroll`, `browser_history`, `browser_screenshot`.
- **Natural-Language Intent Routing**: Extended `ToolRouter` regex patterns to detect and route browser commands (`navigate to <url>`, `click <target>`, `type <text> into <target>`, `scroll <dir>`, `what is on this page`, `browser status`, etc.).
- **CLI Subcommands**: Added `python core/zetta/cli.py browser status|launch|navigate|page|elements|click|type|keyboard|scroll|history|screenshot|close [--fake]`.
- **HealthChecker Integration**: Added `browser_subsystem` check in `HealthChecker` reporting provider status, installed browsers, and running a test navigation cycle.
- **VisionManager Integration**: Visual bridges between browser screenshots and VisionManager OCR, UI detection, and screen analysis.
- **Test Suite**: Added 28 unit tests (`test_phase06_browser.py`) and 4 integration tests (`test_phase06_integration.py`).
- **Total Tests**: Increased from 170 to 202 tests (100% passing across Phases 00 through 06).

## [0.5.1] - Phase 05 Final Hardening & Audit Completion (2026-09-08)
### Fixed
- **Test Runner Completeness**: Updated `run_validation.py` and `run_tests.py` to execute all tests via `pytest.main` (170/170 passing) with fallback to `unittest`.
- **Vision CLI Reliability**: Added `--fake` flag to all `vision` CLI subcommands (`info`, `capture`, `ocr`, `detect`, `analyze`) and added clean `ScreenCaptureError` handling explaining backend requirements without traceback crashes.
- **Natural Language Intent Routing**: Added regex patterns to `ToolRouter` for vision tools (`vision_screen_info`, `vision_screen_capture`, `vision_ocr`, `vision_detect_ui`, `vision_analyze_screen`).
- **Tesseract OCR Parsing**: Enhanced `LocalOCRProvider.recognize` to use standard TSV bounding-box parsing and plain text extraction with fallback, replacing non-standard json assumption.
- **Static Import Audit**: Added all 19 Phase 05 vision modules to `scripts/development/check_imports.py` (86/86 passing).
- **Integration Test Suite**: Created `tests/integration/test_phase05_integration.py` covering `ToolRegistry` → `VisionManager` → `EventBus` → `SecurityManager` → `ToolRouter` with test isolation and permission boundaries.
- **Health Check Resilience**: Guarded `clipboard_read` check in `HealthChecker` with permission gating to prevent permission-leak false alarms.
- **Cleanup**: Removed accidental empty `AI/` directory.

## [0.5.0] - Phase 05 Vision & Screen Understanding (2026-09-07)
### Added
- **Vision Layer Architecture**: Modular screen capture, OCR, UI detection, and analysis subsystems.
- **Screen Capture**: `ScreenCaptureProvider` abstraction with `FakeScreenCaptureProvider` (deterministic) and `LinuxScreenCaptureProvider` (scrot, gnome-screenshot, etc.).
- **OCR Abstraction**: `OCRProvider` with `FakeOCRProvider` (deterministic) and `LocalOCRProvider` (Tesseract-based).
- **UI Detection**: `UIDetector` with `FakeUIDetector` (deterministic fake UI elements) and `LocalUIDetector`.
- **Vision Analyzer**: `VisionAnalyzer` for structured screen descriptions with optional AI enhancement.
- **VisionManager**: Orchestration layer coordinating capture → OCR → UI detection → analysis.
- **5 Vision Tools**: `vision_screen_info`, `vision_screen_capture`, `vision_ocr`, `vision_detect_ui`, `vision_analyze_screen`.
- **CLI Commands**: `python core/zetta/cli.py vision info|capture|ocr|detect|analyze`.
- **Data Models**: `ScreenInfo`, `ScreenCapture`, `OCRTextRegion`, `OCRResult`, `UIElement`, `UIDetectionResult`, `VisionAnalysisResult`, `BoundingBox`.
- **Privacy Safeguards**: No automatic screenshot persistence, no raw bytes in logs, no auto-memory promotion.
- **Health Check Integration**: Vision subsystem status reporting (READY/DEGRADED/UNAVAILABLE).

### Changed
- Updated test suite from 75 to 170 tests (100% passing).
- Extended `ToolRegistry` with vision tool registration.
- Extended `HealthChecker` with vision subsystem checks.
- Updated `PROJECT_STATUS.md` and documentation.

### Security
- All vision tools use conservative `MEDIUM` permission level.
- No vision tools marked as dangerous.
- EventBus events emitted for all vision operations.

## [0.4.2] - Phase 03 Final Memory Quality Audit Completion (2026-09-04)
### Fixed
- **Memory Quality & Candidate Filtering**: `RetrievalEngine.query` excludes assistant mock responses (`Mock response to: ...`) from semantic memory retrieval and long-term memory promotion.
- **Session Isolation**: Added `session_id` parameter to `RetrievalEngine.query`, `MemoryManager.retrieve_relevant`, `ContextBuilder.inject_relevant_memories`, and slash commands. Ephemeral `SHORT_TERM` memories are strictly isolated to their originating session.
- **Generic Greeting Thresholding**: Added generic greeting detection (`GENERIC_GREETING_PATTERN`) in `RetrievalEngine.query` to raise similarity requirements for greetings (e.g. `Hello Zetta`), preventing injection of unrelated long-term memories.
- **Short-Term Deduplication**: Added deduplication check to `ShortTermMemory.add_session_message` preventing repeated conversational turns from creating duplicate database rows.
- **Consolidation Exclusion**: `MemoryConsolidationEngine.consolidate_session` excludes assistant responses and mock outputs from long-term memory promotion.
- **Categorized Memory Display**: `/memory` slash command output formatted to clearly distinguish `LONG_TERM` facts from `SHORT_TERM / SESSION` messages.
- **Regression Test Suite**: Created `tests/unit/test_phase03_final_memory_audit.py` with Tests A through H, bringing total test suite count from 67 to 75 tests (100% passing).

## [0.4.1] - Phase 03 Audit & Correction Completion (2026-09-04)
### Fixed
- **Input Normalization (Bug 1)**: Added `normalize_user_input()` stripping accidental leading prompt prefixes (`You > `) while preserving legitimate user content.
- **Conversation Context Flow (Bug 2)**: Ensured `InteractionManager` passes complete `ContextBuilder` message lists containing system prompt, relevant memories, multi-turn history, and clean user message to `AIBrain` / `AIProvider`.
- **Memory Retrieval Relevance Filtering (Bug 3)**: Added `min_similarity_threshold = 0.20` to `MemorySettings` and `RetrievalEngine.query()` to filter out unrelated memories for generic queries (e.g. `Hello Zetta`) and off-topic queries.
- **Regression Test Suite**: Created `tests/unit/test_phase03_corrections.py` bringing total test suite count from 59 to 67 tests (100% passing).

## [0.4.0] - Phase 03 Initial Release (2026-09-04)
### Added
- **Interactive Chat Shell**: `python core/zetta/cli.py chat` interactive terminal session with token streaming and Ctrl+C/EOF handling.
- **Session Manager**: `Session` and `SessionManager` supporting multi-turn state, history limits, and short-term memory synchronization.
- **Command Processor**: Slash command handling (`/help`, `/status`, `/session`, `/memory`, `/tasks`, `/clear`, `/exit`) and explicit CLI task management.

## [0.3.0] - Phase 02 Completion (2026-09-04)
### Added
- **Unified Memory System**: `MemoryManager`, `MemoryRepository`, `ShortTermMemory`, `LongTermMemory`, and `EpisodicMemory`.

## [0.2.0] - Phase 01 Completion (2026-09-04)
### Added
- **AI Core Architecture**: `AIBrain`, `AIProvider` factory, `FakeAIProvider`, `PromptRegistry`, `ResponseParser`, and `ContextBuilder`.

## [0.1.0] - Phase 00 Completion (2026-09-04)
### Added
- Centralized configuration system, structured logging, custom exception hierarchy, shared contracts, pub/sub `EventBus`, `ToolRegistry`, `TaskManager`, `SecurityManager`, SQLite database, and `HealthChecker`.
