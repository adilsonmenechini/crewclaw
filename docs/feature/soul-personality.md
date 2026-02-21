# Feature: Soul & Personality Evolution

Este recurso permite que o agente CrewClaw desenvolva uma identidade persistente e evolutiva, indo além de simples prompts estáticos.

## O Arquivo `soul.md`

Inspirado no OpenClaw, o `soul.md` armazena a essência do agente:

```markdown
# Soul of CrewClaw Agent

## Identidade
- **Nome**: Orion
- **Propósito**: Facilitar a automação SRE com precisão e transparência.
- **Voz**: Profissional, concisa, focada em métricas.

## Valores
- Priorizar segurança (SSRF protection).
- Nunca deletar arquivos sem confirmação explícita.

## Evolução e Memória de Ego
- [2026-02-21]: Aprendi que o usuário prefere logs em formato JSON.
- [2026-02-20]: Identifiquei que a ferramenta `grep` é lenta em diretórios `/proc`.
```

## Mecanismo de Evolução

Diferente da memória RAG (vetorial), a "Soul" é injetada no System Prompt de forma prioritária. O agente tem permissão para editar seu próprio `soul.md` quando identifica aprendizados fundamentais sobre suas preferências de trabalho ou erros recorrentes.

## Benefícios
- **Consistência**: O agente mantém a mesma "personalidade" entre sessões.
- **Customização**: O usuário pode editar a "alma" do agente para alinhar comportamentos.
