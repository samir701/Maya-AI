# ZETTA AI EMPLOYEE — MEMORY ARCHITECTURE & SPECIFICATION (PHASE 02)

## 1. Overview
The ZETTA Memory System provides local-first, provider-independent persistent and session memory storage, retrieval, deduplication, ranking, and context injection.

## 2. Key Components
- **Memory Contracts (`shared/types`)**:
  - `Memory` dataclass with `MemoryType` (`SHORT_TERM`, `LONG_TERM`, `EPISODIC`, `SEMANTIC`), `MemorySource`, and `MemorySensitivity`.
- **Database Schema (`core/zetta/db/database.py`)**:
  - SQLite tables: `memories`, `memory_tags`, `memory_links`, `memory_history`.
- **Memory Repository (`core/zetta/memory/repository`)**:
  - Encapsulates database CRUD, text query, access tracking, and history logging.
- **Short-Term Memory (`core/zetta/memory/short_term`)**:
  - Ephemeral session memory with strict size limits (`short_term_limit`) and expiration (`short_term_expiration_hours`).
- **Long-Term Memory (`core/zetta/memory/long_term`)**:
  - Persistent user preferences, explicit facts ("Remember this"), and derived knowledge.
- **Episodic Memory (`core/zetta/memory/episodic`)**:
  - Structured history of completed task outcomes and major system events.
- **Embeddings & Vector Store (`core/zetta/memory/embeddings`)**:
  - Abstract `EmbeddingProvider`, offline `FakeEmbeddingProvider` (hash-based cosine similarity), and `LocalVectorStore`.
- **Retrieval & Ranking (`core/zetta/memory/retrieval`)**:
  - Multi-signal scoring engine combining similarity, importance, exponential recency decay, confidence, and source trust.
  - Security filtering via `SecurityManager` based on sensitivity level.
- **Deduplication (`core/zetta/memory/dedup.py`)**:
  - Merges duplicate memories into existing records rather than creating redundant database rows.
- **Expiration & Forgetting (`core/zetta/memory/expiration.py`, `forgetting.py`)**:
  - TTL purge engine and user-directed deletion.
- **Consolidation Engine (`core/zetta/memory/consolidation.py`)**:
  - Promotes high-importance short-term session memories to persistent long-term memory.
- **Context Integration (`core/zetta/ai/context/builder.py`)**:
  - Injects retrieved, budgeted relevant memories into `AIMessage` prompts without exposing DB access directly to AI providers.

## 3. CLI Subcommands
- `python3 core/zetta/cli.py memory list`
- `python3 core/zetta/cli.py memory add <content>`
- `python3 core/zetta/cli.py memory get <id>`
- `python3 core/zetta/cli.py memory delete <id>`
- `python3 core/zetta/cli.py memory search <query>`
- `python3 core/zetta/cli.py memory clear-session <session_id>`
