# ZETTA AI EMPLOYEE — Phase 03 Architecture Documentation

## Overview

Phase 03 implements the **Interaction & Desktop Assistant Shell** for ZETTA AI EMPLOYEE. It builds a decoupled, memory-aware terminal interaction layer connecting:

```
CLI Presentation Layer (ChatShell)
       ↓ (Input Normalization)
InteractionManager / CommandProcessor
       ↓
SessionManager & ShortTermMemory
       ↓
Memory Retrieval (Min Similarity Filtering: 0.20) & ContextBuilder
       ↓
AIBrain & AIProvider (Fake / Real Providers)
       ↓
TaskManager & SecurityManager
       ↓
EventBus Event Publishing
```

---

## Component Architecture

### 1. Interaction Subpackage (`core/zetta/interaction/`)
- `session.py`: `Session` dataclass and `SessionManager` managing multi-turn state, history limits, and short-term memory sync.
- `manager.py`: `InteractionManager` central orchestrator for message processing, input normalization, memory retrieval, task intent detection, and streaming.
- `chat.py`: `ChatShell` presentation shell managing terminal I/O, progressive streaming output, prompt normalization, and Ctrl+C / EOF handling.
- `commands.py`: `CommandProcessor` parsing slash commands (`/help`, `/status`, `/session`, `/memory`, `/tasks`, `/clear`, `/exit`) and explicit task CLI commands.
- `confirmation.py`: `ConfirmationInterface` handling interactive security confirmation prompts for sensitive operations.
- `formatting.py`: Terminal formatting, input normalization (`normalize_user_input`), status reporting, and secret sanitization (`sk-...` masking).

### 2. Input Normalization & Prompt Safety
- `normalize_user_input(raw_input: str)` cleans user inputs by removing accidental prompt prefixes like `You > ` or `You > You > ` resulting from copy-pasting or shell artifacts.
- Guarantees that internal messages sent to `Session`, `MemoryManager`, `ContextBuilder`, `AIBrain`, and `AIProvider` contain only clean user text.
- Preserves internal quotes and references (e.g. `I literally want to say "You > Hello"`).

### 3. Context Flow Guarantee
- `ContextBuilder.build_messages()` constructs ordered message payloads:
  1. System instructions + `[Retrieved Relevant Memory Context]` (if retrieved) + `[Active Task Context]` + `[System Environment]`
  2. Conversation History (`AIMessage(role=USER/ASSISTANT)` for past turns)
  3. Current User Message (`AIMessage(role=USER, content=user_prompt)`)
- `InteractionManager` passes pre-built `messages` payloads directly to `AIBrain.generate()` and `AIBrain.stream_messages()`, ensuring complete context fidelity across both sync and streaming modes.

### 4. Memory Retrieval & Memory Quality Audit
- `RetrievalEngine.query()` enforces a strict separation between Conversation History, Ephemeral Short-Term Memory, and Durable Long-Term User Facts.
- **Candidate Filtering**: Assistant responses (such as `Mock response to: ...`) are excluded from semantic memory retrieval.
- **Session Isolation**: Ephemeral `SHORT_TERM` memories are isolated to their owning session (`session_id`). Cross-session retrieval of ephemeral conversation turns is prevented. `LONG_TERM`, `EPISODIC`, and `SEMANTIC` facts remain globally available.
- **Generic Greetings & Relevance Threshold**: Generic greetings (e.g. `Hello Zetta`, `Thanks`) are filtered so they do not return arbitrary unrelated memories.
- **Deduplication**: `ShortTermMemory` and `MemoryDeduplicator` prevent creating duplicate memory turns or mock responses in database storage.
- **Categorized Display**: Slash command `/memory` groups entries by `LONG_TERM` facts and `SHORT_TERM / SESSION` messages.

### 5. Slash Commands

| Command | Description |
|---|---|
| `/help` | Display command summary |
| `/status` | Display system, provider, memory, and task status |
| `/session` | Display current session ID |
| `/memory` | Summarize stored memories grouped by category |
| `/memory search <query>` | Retrieve memories matching query |
| `/memory clear` | Clear ephemeral session memory |
| `/tasks` | List current system tasks |
| `/clear` | Clear terminal screen |
| `/exit`, `/quit` | Exit chat session |

---

## Verification
- Total Tests: 75 / 75 Passed (59 baseline + 8 Phase 03 correction tests + 8 Memory Quality Audit tests)
- Offline Determinism: 100% (FakeAIProvider)
- System Health: OK across all 9 subsystems
