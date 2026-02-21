# Interactive Onboarding (crewclaw init)

The `crewclaw init` command has been transformed into an interactive assistant that configures the complete environment for you, following onboarding best practices.

## Configuration Flow

When you run the command, CrewClaw will guide you through the following steps:

### 1. Identity (Soul)
- **Your Name**: How the assistant should address you.
- **AI Name**: The name you wish to give your assistant (e.g., Orion, Jarvis, CrewClaw).
- **Main Goal**: Your AI's central mission (e.g., "Helping me with SRE automation").
- **Template Detection**: The system analyzes your goal to automatically load the best initial set of tools and prompts (e.g., SRE, Researcher, Writer).

### 2. LLM and Providers
- **Provider**: Choose between OpenRouter (default), Google, OpenAI, or Anthropic.
- **Model**: Specify the desired model (e.g., `google/gemini-2.0-flash-lite`).
- **API Key**: Access key that will be securely saved in the `.env` file.
- **Fallback (Optional)**: Set up a backup provider in case the primary one is unavailable.

### 3. Integrations (Optional)
- **Telegram**: You can activate Telegram integration by providing a Bot Token.

## Automatically Generated Structure

After completion, CrewClaw creates the following structure:

- **`crewclaw.json`**: Central configuration file with all parameters.
- **`.env`**: Secure storage for API keys.
- **`workspace/memory/soul.md`**: The foundation of your AI's personality and identity.
- **`workspace/agents/assistant.yaml`**: A ready-to-use agent configured with your identity and goal.
- **`workspace/tasks/getting_started.yaml`**: An initial task to test the system.
- **`workspace/skills/hello.md`**: A basic example Python skill (tool).

## How to Run

Simply type in your terminal:

```bash
uv run crewclaw init
```

If you wish to create the directory structure without the interactive assistant:

```bash
uv run crewclaw init --non-interactive
```

---
> [!TIP]
> After init, you can test your new assistant by running:
> `uv run crewclaw run -a assistant "Hello, introduce yourself"`
> 
> Use the `--verbose` flag to follow the AI's detailed reasoning!
