# CrewClaw

Sistema de agentes autônomos com memória persistente local.

## Overview

CrewClaw é um framework de agentes AI que combina:
- **Orquestração**: CrewAI para gestão de múltiplos agentes
- **Memória Vetorial**: SQLite + sqlite-vec para busca semântica
- **Execução Autônoma**: Runtime ReAct com watchdog
- **Privacidade**: 100% local, zero dependência cloud

## Documentação

📚 **Documentação completa**: [docs/adr/](docs/adr/)

### Arquitetura de Decisões (ADR)

| ADR | Título |
|-----|--------|
| [001](docs/adr/001-arquitetura-sistema.md) | Arquitetura Geral do Sistema |
| [002](docs/adr/002-orquestracao-crewai.md) | Orquestração com CrewAI |
| [003](docs/adr/003-memoria-vetorial.md) | Memória Vetorial SQLite-vec |
| [004](docs/adr/004-ferramentas.md) | Sistema de Ferramentas |
| [005](docs/adr/005-runtime-react.md) | Runtime ReAct |
| [006](docs/adr/006-provider-utils.md) | Módulos Provider e Utils |

## Quick Start

### Instalação

```bash
# Clone o repositório
git clone https://github.com/your-org/crewclaw.git
cd crewclaw

# Crie ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# Instale dependências
pip install -r requirements.txt

# Configure as variáveis de ambiente
cp .env.example .env
# Edite .env com suas configurações
```

### Configuração

Edite `crewclaw.json` para ajustar:

```json
{
  "llm": {
    "provider": "openrouter",
    "model": "openrouter/google/gemini-2.5-flash"
  },
  "embedding": {
    "provider": "sentence-transformers",
    "model": "sentence-transformers/all-MiniLM-L6-v2"
  },
  "runtime": {
    "max_iterations": 20,
    "watchdog_enabled": true
  }
}
```

### Executando Agentes

#### Via CLI

```bash
# Executar agente
crewclaw run --agent explorer --task "Analise o projeto"

# Listar agentes disponíveis
crewclaw agents list

# Buscar na memória
crewclaw memory search "conceito relevante"
```

## Estrutura do Projeto

```
crewclaw/
├── crewclaw/
│   ├── agents/       # Factory e Crew
│   ├── cli/          # Interface de linha de comando
│   ├── config/       # Gestão de configuração JSON
│   ├── memory/       # Persistência: SQLite, Markdown, busca híbrida
│   ├── provider/     # Abstrações de provedores de IA (LLM, Embedder)
│   ├── runtime/      # Executor ReAct + Watchdog
│   ├── tools/        # Ferramentas do sistema
│   └── utils/        # Utilitários transversais (logging, errors, text)
├── memory/           # Memória persistente (Markdown + SQLite)
├── logs/             # Logs de execução
└── docs/
    └── adr/          # ADRs
```

## Módulos Principais

### `crewclaw.provider` — Provedores de IA

```python
from crewclaw.provider import LiteLLM, create_llm
from crewclaw.provider import create_embedder, SentenceTransformersEmbedder
from crewclaw.provider import LiteLLMForCrewAI, create_crewai_llm
```

### `crewclaw.utils` — Utilitários

```python
from crewclaw.utils import get_logger, CrewClawError
from crewclaw.utils import truncate, slugify, sanitize_filename
```

## Ferramentas Disponíveis

| Tool | Descrição |
|------|-----------|
| `file_read` | Ler arquivos |
| `file_write` | Escrever arquivos |
| `grep` | Busca por padrões |
| `shell` | Executar comandos |
| `web` | Busca na web |
| `memory_search` | Buscar na memória vetorial |

## Configuração de Agentes

Arquivo: `config/agents.yaml`

```yaml
explorer:
  role: "Code Explorer"
  goal: "Find relevant code patterns"
  backstory: "Expert at analyzing codebases"
  tools:
    - file_read
    - grep
  max_iter: 10
```

## Ambiente

| Variável | Descrição |
|----------|-----------|
| `CREWCLAW_CONFIG` | Path para config JSON |
| `CREWCLAW_AGENTS_CONFIG` | Path para agents YAML |
| `OPENROUTER_API_KEY` | API key para LLM |

## License

MIT
