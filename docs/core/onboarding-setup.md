# Interactive Onboarding (crewclaw init)

O comando `crewclaw init` foi transformado em um assistente interativo que configura o ambiente completo para você, seguindo as melhores práticas de onboarding.

## Fluxo de Configuração

Ao executar o comando, o CrewClaw guiará você pelos seguintes passos:

### 1. Identidade (Soul)
- **Seu Nome**: Como o assistente deve se referir a você.
- **Nome da IA**: O nome que você deseja dar ao seu assistente (ex: Orion, Jarvis, CrewClaw).
- **Objetivo Principal**: A missão central da sua IA (ex: "Me ajudar com automação SRE").
- **Deteção de Template**: O sistema analisa seu objetivo para carregar automaticamente o melhor conjunto inicial de ferramentas e prompts (ex: SRE, Researcher, Writer).

### 2. LLM e Provedores
- **Provedor**: Escolha entre OpenRouter (padrão), Google, OpenAI ou Anthropic.
- **Modelo**: Especifique o modelo desejado (ex: `google/gemini-2.0-flash-lite`).
- **API Key**: Chave de acesso que será salva de forma segura no arquivo `.env`.
- **Fallback (Opcional)**: Configure um provedor de reserva caso o principal esteja indisponível.

### 3. Integrações (Opcional)
- **Telegram**: Você pode ativar a integração com o Telegram fornecendo o Bot Token.

## O que o comando gera automaticamente

Após o preenchimento, o CrewClaw cria a seguinte estrutura:

- **`crewclaw.json`**: Arquivo de configuração central com todos os parâmetros.
- **`.env`**: Armazenamento seguro de chaves de API.
- **`workspace/memory/soul.md`**: A base da personalidade e identidade da sua IA.
- **`workspace/agents/assistant.yaml`**: Um agente pronto, configurado com sua identidade e objetivo.
- **`workspace/tasks/getting_started.yaml`**: Uma tarefa inicial para testar o sistema.
- **`workspace/skills/hello.md`**: Uma skill (ferramenta) Python básica de exemplo.

## Como Executar

Simplesmente digite no seu terminal:

```bash
uv run crewclaw init
```

Se desejar apenas criar a estrutura de diretórios sem o assistente interativo:

```bash
uv run crewclaw init --non-interactive
```

---
> [!TIP]
> Após o init, você pode testar seu novo assistente rodando:
> `uv run crewclaw run -a assistant "Olá, apresente-se"`
> 
> Use a flag `--verbose` para acompanhar o raciocínio detalhado da IA!
