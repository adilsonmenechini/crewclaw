# ADR 006: Separação de Módulos `provider/` e `utils/`

## 1. Status

**Aceito** — Implementado na versão 1.1.0

## 2. Contexto

Na versão 1.0, certas abstrações foram colocadas em módulos incorretos:

- `memory/llm.py`, `memory/embedder.py`, `memory/crewai_llm.py` — código de **provedor de IA** (LiteLLM, OpenAI embeddings, sentence-transformers) estava dentro do módulo de memória, causando acoplamento desnecessário.
- `config/logging.py`, `config/errors.py` — utilitários **transversais** (logging, exceções) estavam misturados com a gestão de configuração.
- `provider/` e `utils/` existiam como diretórios vazios sem código.

### Problema

A estrutura causava:
- Dificuldade de descoberta: onde fica o LLM? Em `memory`? Em `config`?
- Acoplamento: quem quer usar o LLM precisa importar de `memory`
- Stagnação: módulos `provider/` e `utils/` estavam criados mas vazios

## 3. Decisão

Reorganizar o código movendo cada arquivo para o módulo semanticamente correto, mantendo **stubs de compatibilidade** nos locais antigos para não quebrar imports existentes.

### 3.1 Módulo `provider/`

Contém todas as abstrações de provedores externos de IA:

| Arquivo | Responsabilidade |
|---------|-----------------|
| `provider/llm.py` | Abstração `LLM` + `LiteLLM` com suporte a 100+ providers |
| `provider/embedder.py` | `Embedder`, `OpenAIEmbedder`, `SentenceTransformersEmbedder` |
| `provider/crewai.py` | `LiteLLMForCrewAI` — wrapper compatível com interface CrewAI |

### 3.2 Módulo `utils/`

Contém utilitários transversais usados por todos os módulos:

| Arquivo | Responsabilidade |
|---------|-----------------|
| `utils/logging.py` | `get_logger`, `setup_logging` |
| `utils/errors.py` | Hierarquia de exceções (`CrewClawError` e subclasses) |
| `utils/text.py` | Helpers de texto: `truncate`, `slugify`, `sanitize_filename`, etc. |

### 3.3 Stubs de Compatibilidade

Os arquivos antigos foram substituídos por stubs que re-exportam do novo local:

```python
# crewclaw/memory/llm.py (stub)
from ..provider.llm import LLM, LiteLLM, create_llm  # noqa: F401
```

Isso garante que código existente que usa `from crewclaw.memory import LLM` continue funcionando.

## 4. Nova Estrutura de Diretórios

```
crewclaw/
├── agents/           # Factory e Crew
├── cli/              # Interface de linha de comando
├── config/           # Gestão de configuração JSON
│   ├── __init__.py   # Config singleton
│   ├── errors.py     # Stub → utils/errors.py
│   └── logging.py    # Stub → utils/logging.py
├── memory/           # Persistência: SQLite, Markdown, busca híbrida
│   ├── llm.py        # Stub → provider/llm.py
│   ├── embedder.py   # Stub → provider/embedder.py
│   ├── crewai_llm.py # Stub → provider/crewai.py
│   └── ...           # database, vectorstore, chunker, etc.
├── provider/         # ★ NOVO: Abstrações de provedores de IA
│   ├── __init__.py
│   ├── llm.py        # LLM, LiteLLM, create_llm
│   ├── embedder.py   # Embedder e implementações
│   └── crewai.py     # LiteLLMForCrewAI
├── runtime/          # Executor ReAct + Watchdog
├── tools/            # Ferramentas do sistema
└── utils/            # ★ NOVO: Utilitários transversais
    ├── __init__.py
    ├── logging.py    # get_logger, setup_logging
    ├── errors.py     # Hierarquia de exceções
    └── text.py       # truncate, slugify, sanitize_filename
```

## 5. Consequências

### 5.1 Vantagens

- **Separação de responsabilidades** clara: provider = AI APIs, utils = infra interna
- **Descobribilidade**: imports intuitivos (`from crewclaw.provider import LiteLLM`)
- **Testabilidade**: módulos menores e independentes
- **Backward compatibility** total via stubs

### 5.2 Custos

- Dois níveis de indireção (stub → provider) — custo mínimo em runtime
- Stubs legados devem ser removidos em versão futura (v2.0)

## 6. Imports Canônicos (pós-refactoring)

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

## 7. Referências

- [ADR 001](001-arquitetura-sistema.md) — Arquitetura Geral
- [ADR 003](003-memoria-vetorial.md) — Memória Vetorial
