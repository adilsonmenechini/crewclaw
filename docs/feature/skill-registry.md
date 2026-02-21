# Feature: Registro de Skills Modular (Inspired by OpenClaw)

Este documento descreve a implementação de um sistema de "Skills" modular no CrewClaw, permitindo que novas capacidades sejam adicionadas via arquivos de configuração simples, sem necessidade de alteração no core do framework.

## Conceito

Inspirado no sistema de `SKILL.md` do OpenClaw e no ClawHub, este sistema permite:
1.  **Definição Declarativa**: Ferramentas definidas em Markdown ou YAML.
2.  **Meta-informação Rica**: Descrições detalhadas, exemplos de uso e restrições.
3.  **Carregamento Dinâmico**: O `SkillsLoader` lê uma pasta ou repositório remoto e registra as ferramentas automaticamente no runtime.

## Estrutura de uma Skill (`SKILL.md`)

```markdown
---
name: "github_search"
description: "Busca repositórios no GitHub por palavras-chave"
parameters:
  query: "String de busca"
  language: "Linguagem de programação (opcional)"
---

# GitHub Search Skill

Esta skill permite ao agente interagir com a API do GitHub.

## Exemplos
- `github_search(query="crewai", language="python")`

## Implementação (Code Block)
```python
import requests

def execute(query, language=None):
    url = f"https://api.github.com/search/repositories?q={query}"
    if language:
        url += f"+language:{language}"
    # ... lógica de requisição ...
    return results
\```
```

## Benefícios
- **Sharing**: Facilidade para a comunidade compartilhar novas skills.
- **Portabilidade**: Skills podem ser baixadas e usadas instantaneamente.
- **Segurança**: Possibilidade de sandbox para a execução de código de skills externas.
