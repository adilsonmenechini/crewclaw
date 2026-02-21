# ADR 006: Separation of `provider/` and `utils/` Modules

## 1. Status

**Accepted** — Implemented in version 1.1.0

## 2. Context

In version 1.0, certain abstractions were placed in incorrect modules:

- `memory/llm.py`, `memory/embedder.py`, `memory/crewai_llm.py` — **AI provider** code (LiteLLM, OpenAI embeddings, sentence-transformers) was inside the memory module, causing unnecessary coupling.
- `config/logging.py`, `config/errors.py` — **Cross-cutting** utilities (logging, exceptions) were mixed with configuration management.
- `provider/` and `utils/` existed as empty directories without code.

### Problem

The structure caused:
- Difficulty in discovery: where does the LLM reside? In `memory`? In `config`?
- Coupling: anyone wanting to use the LLM had to import from `memory`.
- Stagnation: `provider/` and `utils/` modules were created but empty.

## 3. Decision

Reorganize the code by moving each file to the semantically correct module, while maintaining **compatibility stubs** in the old locations to avoid breaking existing imports.

### 3.1 `provider/` Module

Contains all abstractions for external AI providers:

| File | Responsibility |
|---------|-----------------|
| `provider/llm.py` | `LLM` + `LiteLLM` abstraction with support for 100+ providers. |
| `provider/embedder.py` | `Embedder`, `OpenAIEmbedder`, `SentenceTransformersEmbedder`. |
| `provider/crewai.py` | `LiteLLMForCrewAI` — wrapper compatible with the CrewAI interface. |

### 3.2 `utils/` Module

Contains cross-cutting utilities used by all modules:

| File | Responsibility |
|---------|-----------------|
| `utils/logging.py` | `get_logger`, `setup_logging`. |
| `utils/errors.py` | Exception hierarchy (`CrewClawError` and subclasses). |
| `utils/text.py` | Text helpers: `truncate`, `slugify`, `sanitize_filename`, etc. |

### 3.3 Compatibility Stubs

Old files were replaced by stubs that re-export from the new location:

```python
# crewclaw/memory/llm.py (stub)
from ..provider.llm import LLM, LiteLLM, create_llm  # noqa: F401
```

This ensures that existing code using `from crewclaw.memory import LLM` continues to work.

## 4. New Directory Structure

```
crewclaw/
├── agents/           # Factory and Crew
├── cli/              # Command line interface
├── config/           # JSON configuration management
│   ├── __init__.py   # Config singleton
│   ├── errors.py     # Stub → utils/errors.py
│   └── logging.py    # Stub → utils/logging.py
├── memory/           # Persistence: SQLite, Markdown, hybrid search
│   ├── llm.py        # Stub → provider/llm.py
│   ├── embedder.py   # Stub → provider/embedder.py
│   ├── crewai_llm.py # Stub → provider/crewai.py
│   └── ...           # database, vectorstore, chunker, etc.
├── provider/         # ★ NEW: AI provider abstractions
│   ├── __init__.py
│   ├── llm.py        # LLM, LiteLLM, create_llm
│   ├── embedder.py   # Embedder and implementations
│   └── crewai.py     # LiteLLMForCrewAI
├── runtime/          # ReAct executor + Watchdog
├── tools/            # System tools
└── utils/            # ★ NEW: Cross-cutting utilities
    ├── __init__.py
    ├── logging.py    # get_logger, setup_logging
    ├── errors.py     # Exception hierarchy
    └── text.py       # truncate, slugify, sanitize_filename
```

## 5. Consequences

### 5.1 Advantages

- **Clear separation of responsibilities**: provider = AI APIs, utils = internal infra.
- **Discoverability**: intuitive imports (`from crewclaw.provider import LiteLLM`).
- **Testability**: smaller, independent modules.
- **Full backward compatibility** via stubs.

### 5.2 Costs

- Two levels of indirection (stub → provider) — minimal runtime cost.
- Legacy stubs should be removed in a future version (v2.0).

## 6. Canonical Imports (Post-refactoring)

```python
# LLM
from crewclaw.provider import LiteLLM, create_llm

# Embeddings
from crewclaw.provider import create_embedder, SentenceTransformersEmbedder

# CrewAI adapter
from crewclaw.provider import LiteLLMForCrewAI, create_crewai_llm

# Utils
from crewclaw.utils import get_logger, CrewClawError, truncate
```

## 7. References

- [ADR 001](001-system-architecture.md) — General Architecture
- [ADR 003](003-vector-memory.md) — Vector Memory
