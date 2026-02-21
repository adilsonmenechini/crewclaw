# CrewClaw

Sistema de agentes autônomos com memória persistente local.

## Overview

CrewClaw é um framework de agentes AI que combina:
- **Orquestração**: CrewAI para gestão de múltiplos agentes
- **Memória Vetorial**: SQLite + sqlite-vec para busca semântica
- **Execução Autônoma**: Runtime ReAct com watchdog e Heartbeat
- **Skills Dinâmicas**: Registro de ferramentas via arquivos Markdown/YAML
- **Identidade e Alma**: Personalidade evolutiva do agente
- **Privacidade**: 100% local, zero dependência cloud

## Documentação

📚 **Guia de Início Rápido e Índice**: [docs/000-index.md](docs/000-index.md)

### Conceitos Principais

| Guia | Descrição |
|------|-----------|
| [Skills, Agents, and Tasks](docs/core/triad-orchestration.md) | A tríade fundamental de orquestração do CrewClaw |
| [Módulos Avançados](docs/features/advanced-modules.md) | Soul, Heartbeat, Hooks, Bridge e Auto-melhoria |

### Arquitetura de Decisões (ADR)

Grouped by evolution and major decisions. [Ver todos os ADRs](docs/adr/)

## Quick Start

### Instalação

```bash
# Clone o repositório
git clone https://github.com/your-org/crewclaw.git
cd crewclaw

# Instale via pip (modo editável recomendado)
pip install -e .
```

### 🚀 Onboarding Inteligente (Recomendado)

O CrewClaw possui um assistente que configura tudo para você, desde o provedor de LLM até a identidade inicial da sua IA.

```bash
crewclaw init
```

Este comando irá:
1. Configurar o **provedor e modelo** de LLM.
2. Definir a **identidade** (Soul) e o objetivo central do seu agente.
3. Criar uma estrutura de **workspace** com agentes e tasks prontos para uso.

---

## Como Usar

### 1. Rodar um Agente
Após o `init`, você pode rodar o assistente padrão:
```bash
uv run crewclaw run -a assistant "Resuma os arquivos do meu projeto"
```

Para ver logs detalhados de execução (pensamentos da IA, ferramentas sendo chamadas):
```bash
uv run crewclaw run -a assistant "Resuma o projeto" --verbose
```

### 2. Buscar na Memória
O CrewClaw indexa automaticamente seus arquivos Markdown em `workspace/memory/`:
```bash
uv run crewclaw search "objetivos do projeto"
```

### 3. Personalizar o Workspace
Toda a lógica está no diretório `workspace/`:
- **`agents/`**: Defina novos agentes via YAML.
- **`tasks/`**: Agende missões específicas.
- **`skills/`**: Crie ferramentas Python dinâmicas usando Markdown.

---

## Estrutura do Projeto

```
workspace/
├── memory/           # Soul (identidade), .md indexados e SQLite
├── agents/           # Configurações dinâmicas de agentes (.yaml)
├── tasks/            # Definições de missões (.yaml)
├── skills/           # Ferramentas personalizadas (.md)
├── mcp/              # Integrações via Model Context Protocol
└── custom_tools/     # Ferramentas Python nativas
```

## Configuração Avançada

O arquivo `crewclaw.json` (gerado pelo `init`) permite ajustes finos:
```json
{
  "llm": {
    "provider": "openrouter",
    "model": "google/gemini-2.0-flash-lite",
    "fallback": { "provider": "google", "model": "gemini-2.0-flash" }
  },
  "telegram": { "enabled": false }
}
```

## Documentação Completa
📚 [docs/000-index.md](docs/000-index.md)

## License
MIT
