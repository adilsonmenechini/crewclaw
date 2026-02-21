# ADR 001: General Architecture of the CrewClaw System

## 1. Status

**Accepted** - Implemented in version 1.0.0

## 2. Context

CrewClaw is an autonomous agent system with local persistent memory, designed for:
- **Total Privacy**: All data remains on the local disk.
- **Autonomous Execution**: Ability to execute tasks in a ReAct loop.
- **Long-term Memory**: Vectorization and semantic search with Markdown persistence.

### Problem to Solve

Traditional AI agent systems depend on external APIs and ephemeral memory. We need a solution that:
- Does not depend on cloud services for persistence.
- Allows full auditability of the agent's "decisions".
- Executes autonomously with protection against infinite loops.

## 3. Architecture Decisions

### 3.1 Technological Stack

| Component | Technology | Rationale |
|------------|------------|---------------|
| **Language** | Python 3.10+ | CrewAI ecosystem, flexibility |
| **Orchestrator** | CrewAI | Native ReAct loop, multi-agent management |
| **Vector Database** | SQLite + sqlite-vec | Local-first, hybrid SQL+vector search |
| **Embeddings** | sentence-transformers (local) | Privacy, no external API |
| **Persistence** | Markdown files | Human auditability |

### 3.2 Directory Structure

```
crewclaw/
├── crewclaw/
│   ├── agents/          # Factory and agent definitions
│   ├── tools/           # System tools
│   ├── runtime/         # ReAct executor
│   ├── config/          # Configuration management
│   └── __init__.py
├── memory/              # Persistent memory (Markdown + SQLite)
├── config/              # YAML configurations
├── logs/                # Execution logs
└── docs/                # Documentation
```

### 3.3 Architecture Diagram

```mermaid
graph TB
    subgraph "Interface"
        CLI[CLI / API]
        MD[Markdown Files]
    end

    subgraph "Core Engine"
        CF[Config Manager]
        AF[Agent Factory]
        RT[ReAct Runtime]
    end

    subgraph "Orchestration"
        AG[CrewAI Agents]
        CR[Crew Manager]
    end

    subgraph "Tools"
        FR[File Read]
        FW[File Write]
        GR[Grep]
        WS[Web Search]
        SH[Shell]
    end

    subgraph "Memory"
        VS[(SQLite-vec)]
        MV[Markdown Files]
        MB[Memory Search]
    end

    CLI --> CF
    MD --> MB
    CF --> AF
    AF --> AG
    AG --> CR
    CR --> RT
    RT --> FR
    RT --> FW
    RT --> GR
    RT --> WS
    RT --> SH
    MB --> VS
    MB --> MV
```

### 3.4 Execution Flow

```mermaid
sequenceDiagram
    participant U as User
    participant C as CLI
    participant A as Agent Factory
    participant R as ReAct Runtime
    participant T as Tools
    participant M as Memory

    U->>C: Executes command
    C->>A: Creates agents
    A->>R: Initializes runtime
    R->>T: Executes tool
    T->>M: Searches context
    M-->>T: Returns result
    T-->>R: Action result
    R->>R: Evaluates completeness
    R->>C: Returns result
    C-->>U: Final output
```

## 4. Component Design

### 4.1 Config Manager

- Singleton that loads `crewclaw.json`.
- Supports dot-notation (`runtime.max_iterations`).
- Environment variables for overrides.

### 4.2 Agent Factory

- Loads agents from `config/agents.yaml`.
- Supports injection of custom tools.
- Variable substitution `{$var}` in prompts.

### 4.3 ReAct Runtime

- Autonomous loop with iteration limit.
- Watchdog to detect infinite loops.
- Auto-correction in case of error.

### 4.4 Memory System

- **Scope**: /agent, /project, /company.
- **Hybrid Search**: FTS5 + vector.
- **Consolidation**: Automatic summary after N tasks.

## 5. Consequences

### 5.1 Advantages

- **Privacy**: Zero cloud dependency.
- **Auditability**: Human-readable Markdown.
- **Flexibility**: Python + YAML + Markdown.
- **Performance**: SQLite-vec is extremely fast.

### 5.2 Limitations

- Installation requires SQLite drivers.
- Local embeddings are slower than API.
- Not distributed (single-node).

## 6. References

- [ADR Template](https://github.com/joelparkerhenderson/architecture-decision-record)
- [CrewAI Documentation](https://docs.crewai.com/)
- [sqlite-vec](https://github.com/asg017/sqlite-vec)
