"""CLI interface for CrewClaw."""

import json
import sys
from pathlib import Path

import yaml

import click
from rich.console import Console
from rich.table import Table

from crewclaw.agent.memory import HybridSearch, get_database
from crewclaw.config import get_config
from crewclaw.config.logging import setup_logging

console = Console()


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def cli(verbose: bool) -> None:
    """CrewClaw - Local-first autonomous agents."""
    level = "INFO" if verbose else "ERROR"
    setup_logging(level_override=level)


@cli.command()
@click.argument("topic", required=False, default="all")
def help(topic: str) -> None:
    """Show help documentation.

    Topics: all, memory, search, runtime, architecture
    """
    docs = {
        "all": """# CrewClaw - Documentação Completa

## Visão Geral
CrewClaw é um sistema de agentes autônomos local-first que combina:
- **CrewAI** para orquestração de agentes
- **SQLite + sqlite-vec** para memória vetorial
- **Markdown** para persistência transparente
- **LiteLLM** para suporte a múltiplos provedores de LLM

## Quick Start

```bash
# Inicializar
crewclaw init

# Definir API key
export OPENROUTER_API_KEY="sua-key"

# Rodar agente
crewclaw run researcher "Pesquise sobre Python"

# Buscar na memória
crewclaw search "o que eu te disse sobre projetos"
```

## Configuração (crewclaw.json)

```json
{
  "llm": {
    "provider": "openrouter",
    "model": "openrouter/google/gemini-2.0-flash-lite"
  },
  "embedding": {
    "provider": "litellm"
  }
}
```
""",
        "memory": """# Sistema de Memória

## Arquitetura Híbrida
- **Camada de Transparência (Markdown):** Arquivos .md no disco
- **Camada de Recuperação (SQLite + Vetores):** Indexação e busca

## Como funciona
1. **Captura:** Identifica fatos importantes durante a conversa
2. **Escrita:** Atualiza arquivos Markdown
3. **Indexação:** Monitora alterações e atualiza o banco vetorial
4. **Recuperação:** Busca semântica usando RAG

## Configuração de Memória
```json
{
  "memory": {
    "scopes": ["/agent", "/project"],
    "retention_days": 90,
    "auto_consolidate": true
  }
}
```
""",
        "search": """# Busca Híbrida

## Componentes
1. **FTS5 (Full Text Search):** Busca por termos exatos
2. **Busca Vetorial:** Busca por significado/semântica
3. **Reranker:** Combina resultados com peso

## Estratégia de Chunking
- Syntax-aware: Reconhece cabeçalhos, listas, código
- Overlap: 10-15% de sobreposição entre chunks
- Hash: Deduplicação por conteúdo

## Consulta
```bash
crewclaw search "meus projetos" --limit 5
```
""",
        "runtime": """# Runtime ReAct

## Ciclo de Execução
1. **Thought:** LLM decide o que fazer
2. **Action:** Executa uma ferramenta
3. **Observation:** Recebe o resultado
4. **Repetição:** Até completar a tarefa

## Componentes
- **Tool Sandbox:** Execução isolada de comandos
- **Context Window:** Gerencia limite de tokens
- **Watchdog:** Evita loops infinitos

## Configuração
```json
{
  "runtime": {
    "max_iterations": 20,
    "watchdog_enabled": true,
    "watchdog_threshold": 3
  }
}
```
""",
        "architecture": """# Arquitetura

## Diagrama do Sistema

```
User → Agent → Tools
           ↓
        Memory → SQLite (FTS5 + Vec)
           ↓
        Markdown Files
```

## Stack Tecnológico
- **Orquestração:** CrewAI
- **Memória Vetorial:** sqlite-vec
- **LLM:** LiteLLM (OpenRouter, Gemini, OpenAI, Anthropic)
- **Embeddings:** sentence-transformers ou LiteLLM

## Providers Suportados
| Provider | Modelo | Variável |
|----------|--------|----------|
| OpenRouter | gemini-2.0-flash-lite | OPENROUTER_API_KEY |
| Gemini | gemini-2.0-flash | GEMINI_API_KEY |
| OpenAI | gpt-4o-mini | OPENAI_API_KEY |
| Anthropic | claude-3.5-sonnet | ANTHROPIC_API_KEY |
""",
    }

    if topic not in docs:
        console.print(f"[red]Tópico '{topic}' não encontrado.[/red]")
        console.print(f"Disponíveis: {', '.join(docs.keys())}")
        return

    console.print(docs[topic])


@cli.command()
@click.argument("task")
@click.option("--agent", "-a", default="router", help="Agent to use (default: router)")
@click.option("--session", "-s", default=None, help="Session ID for conversation memory")
@click.option("--verbose", is_flag=True, help="Enable verbose output")
@click.pass_context
def run(ctx: click.Context, task: str, agent: str, session: str | None, verbose: bool) -> None:
    """Run an agent on a task.

    If no agent is specified, defaults to 'router' which automatically
    delegates to the appropriate specialist.

    Available agents: router, researcher, writer, analyzer, sre, librarian,
                     simple, full, heartbeat

    Examples:
        crewclaw run "O que é Python?"           # Uses router (default)
        crewclaw run -a researcher "Pesquise X"   # Uses researcher
        crewclaw run -a writer "Escreva um arquivo"
        crewclaw run -s my-session "continuar..."  # Continue from previous session
    """
    try:
        from crewai import Task
        from crewclaw.agent.samples import get_sample_agent
        from crewclaw.session import get_current_session, set_session

        # Set up session with memory
        if session:
            session_mgr = set_session(session)
        else:
            session_mgr = get_current_session()

        # Load context from previous conversations
        context_messages = session_mgr.load_context()

        # Build context string for system prompt
        context_str = ""
        if context_messages:
            context_str = "\n\n".join(
                [f"{msg['role'].upper()}: {msg['content']}" for msg in context_messages]
            )
            context_str = f"\n\nIMPORTANT CONTEXT FROM PREVIOUS CONVERSATIONS:\n{context_str}\n\nUse this context to provide more personalized responses."

        # Get verbose flag from parent context
        verbose = ctx.parent.params.get("verbose", False)

        if agent == "router":
            from crewclaw.agent.samples import get_sample_agent

            router = get_sample_agent("router")
            router.verbose = verbose

            # Add context to task description
            full_task = f"{task}{context_str}"

            task_obj = Task(
                description=full_task,
                expected_output="A helpful response analyzing the task and using appropriate tools",
                agent=router,
            )

            result = router.execute_task(task_obj)
        else:
            agent_obj = get_sample_agent(agent)
            agent_obj.verbose = verbose

            full_task = f"{task}{context_str}"

            task_obj = Task(
                description=full_task,
                expected_output="A helpful response",
                agent=agent_obj,
            )

            result = agent_obj.execute_task(task_obj)

        # Save conversation to memory
        session_mgr.add_message("user", task)
        session_mgr.add_message("assistant", result)

        console.print(f"\n[bold green]Result:[/bold green]\n{result}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.argument("query")
@click.option("--limit", "-n", default=5, help="Maximum results")
def search(query: str, limit: int) -> None:
    """Search memory."""
    try:
        search_engine = HybridSearch()
        results = search_engine.search(query, limit)

        table = Table(title=f"Search results for: {query}")
        table.add_column("Score", style="cyan")
        table.add_column("Content", style="white")

        for result in results:
            table.add_row(
                f"{result.score:.3f}",
                result.content[:100] + "..." if len(result.content) > 100 else result.content,
            )

        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
def status() -> None:
    """Show system status."""
    config = get_config()

    table = Table(title="CrewClaw Status")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Project", config.get("project.name", "unknown"))
    table.add_row("Memory Dir", config.get("project.memory_dir", "unknown"))
    table.add_row("Embedder", config.get("embedding.provider", "unknown"))
    table.add_row(
        "Vector Count",
        str(get_database().connection.execute("SELECT COUNT(*) FROM vectors").fetchone()[0]),
    )

    console.print(table)


@cli.command()
@click.option("--path", "-p", default="./workspace/memory", help="Path to initialize")
@click.option("--non-interactive", is_flag=True, help="Skip interactive setup")
def init(path: str, non_interactive: bool) -> None:
    """Initialize CrewClaw with interactive setup."""

    console.print("\n[bold blue]Welcome to CrewClaw![/bold blue] 🚀")
    console.print("Let's configure your local agent environment.\n")

    if non_interactive:
        _perform_basic_init(path)
        console.print(f"[green]Initialized basic memory directory:[/green] {path}")
        return

    # 1. Identity
    user_name = click.prompt("What is your name?", default="User")
    ai_name = click.prompt("What should I call myself? (AI Name)", default="Orion")
    objective = click.prompt(
        "What is my main objective?", default="Assist with SRE, automation and task management"
    )

    # 2. LLM Config
    console.print("\n[bold cyan]LLM Configuration[/bold cyan]")
    provider = click.prompt(
        "Select LLM Provider",
        type=click.Choice(["openrouter", "google", "openai", "anthropic"]),
        default="openrouter",
    )
    model = click.prompt("Select Model", default="google/gemini-2.0-flash-lite")
    api_key = click.prompt("Enter API Key", hide_input=True)

    # 3. Fallback (Optional)
    use_fallback = click.confirm("Do you want to configure a fallback provider?", default=False)
    fallback_config = None
    if use_fallback:
        f_provider = click.prompt("Fallback Provider", default="google")
        f_model = click.prompt("Fallback Model", default="gemini-2.0-flash")
        fallback_config = {"provider": f_provider, "model": f_model}

    # 4. Telegram (Optional)
    console.print("\n[bold cyan]Integrations[/bold cyan]")
    use_telegram = click.confirm("Do you want to enable Telegram?", default=False)
    telegram_token = None
    if use_telegram:
        telegram_token = click.prompt("Enter Telegram Bot Token", hide_input=True)

    # 5. Generate Files
    _perform_basic_init(path)
    _save_config(
        path, user_name, ai_name, objective, provider, model, fallback_config, use_telegram
    )
    _save_env(provider, api_key, telegram_token)
    _create_workspace_templates(ai_name, objective)

    console.print("\n[bold green]Success![/bold green] CrewClaw is ready.")
    console.print(f"Identity: [bold]{ai_name}[/bold]")
    console.print(f"Goal: {objective}")
    console.print("\nNext steps:")
    console.print("1. Run `crewclaw run -a assistant 'Hello'` to test.")
    console.print("2. Explore [bold]docs/000-index.md[/bold] for more details.")


def _perform_basic_init(path: str) -> None:
    """Create basic memory structure."""
    mem_dir = Path(path)
    mem_dir.mkdir(parents=True, exist_ok=True)

    welcome = mem_dir / "welcome.md"
    if not welcome.exists():
        welcome.write_text(
            """# Welcome to CrewClaw

This is your local memory directory. Files here will be indexed
and available for semantic search.

## Getting Started

1. Add Markdown files to this directory
2. Run `crewclaw index` to index them
3. Use `crewclaw search <query>` to find information
"""
        )


def _save_config(
    path, user_name, ai_name, objective, provider, model, fallback, use_telegram
) -> None:
    """Save configuration to crewclaw.json."""
    config_file = Path("crewclaw.json")
    from crewclaw.config import get_config

    cfg = get_config()._get_defaults()

    cfg["project"]["memory_dir"] = str(path)
    cfg["project"]["database_path"] = str(Path(path) / "crewclaw.db")
    cfg["project"]["soul_path"] = str(Path(path) / "soul.md")

    cfg["user"]["name"] = user_name
    cfg["ai"]["name"] = ai_name
    cfg["ai"]["objective"] = objective

    cfg["llm"]["provider"] = provider
    cfg["llm"]["model"] = model

    # Detect correct env var
    env_vars = {
        "openrouter": "OPENROUTER_API_KEY",
        "google": "GEMINI_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
    }
    cfg["llm"]["api_key_env"] = env_vars.get(provider, "OPENROUTER_API_KEY")

    if fallback:
        cfg["llm"]["fallback"] = fallback

    cfg["telegram"]["enabled"] = use_telegram

    with open(config_file, "w") as f:
        json.dump(cfg, f, indent=2)


def _save_env(provider, api_key, telegram_token) -> None:
    """Save API keys to .env."""
    env_file = Path(".env")
    lines = []
    if env_file.exists():
        lines = env_file.read_text().splitlines()

    # Map provider to env var
    env_var = "OPENROUTER_API_KEY"
    if provider == "google":
        env_var = "GEMINI_API_KEY"
    elif provider == "openai":
        env_var = "OPENAI_API_KEY"
    elif provider == "anthropic":
        env_var = "ANTHROPIC_API_KEY"

    # Update or add
    found_llm = False
    found_tg = False
    new_lines = []
    for line in lines:
        if line.startswith(f"{env_var}="):
            new_lines.append(f"{env_var}={api_key}")
            found_llm = True
        elif line.startswith("TELEGRAM_BOT_TOKEN=") and telegram_token:
            new_lines.append(f"TELEGRAM_BOT_TOKEN={telegram_token}")
            found_tg = True
        else:
            new_lines.append(line)

    if not found_llm:
        new_lines.append(f"{env_var}={api_key}")
    if not found_tg and telegram_token:
        new_lines.append(f"TELEGRAM_BOT_TOKEN={telegram_token}")

    env_file.write_text("\n".join(new_lines) + "\n")


def _create_workspace_templates(ai_name, objective) -> None:
    """Create initial workspace files using templates."""
    from crewclaw.agent.samples import find_best_template

    # Find best template based on user objective
    template = find_best_template(objective)

    # 1. Soul
    soul_path = Path("./workspace/memory/soul.md")
    soul_path.parent.mkdir(parents=True, exist_ok=True)
    if not soul_path.exists():
        soul_path.write_text(
            f"""# Soul of {ai_name}

## Identity
- **Name**: {ai_name}
- **Purpose**: {objective}
- **Voice**: {template.get("voice", "Helpful, analytical, and precise.")}

## Values
- Prioritize security and privacy.
- Be transparent about tool usage.
- Learn from interactions to improve assistance.

## Evolution
- [{Path(__file__).parent.parent.parent.name}] Inicializado via onboarding interativo usando template: {template['role']}.
"""
        )

    # 2. Agent
    agents_dir = Path("./workspace/agents")
    agents_dir.mkdir(parents=True, exist_ok=True)
    assistant_yaml = agents_dir / "assistant.yaml"
    if not assistant_yaml.exists():
        agent_cfg = {
            "assistant": {
                "role": f"{ai_name} - {template['role']}",
                "goal": objective,
                "backstory": f"You are {ai_name}. {template['backstory']}",
                "tools": template["tools"],
                "verbose": True,
            }
        }
        if template.get("allow_delegation"):
            agent_cfg["assistant"]["allow_delegation"] = True

        with open(assistant_yaml, "w") as f:
            yaml.dump(agent_cfg, f)

    # 3. Task
    tasks_dir = Path("./workspace/tasks")
    tasks_dir.mkdir(parents=True, exist_ok=True)
    start_task = tasks_dir / "getting_started.yaml"
    if not start_task.exists():
        task_cfg = {
            "hello_task": {
                "description": f"Introduce yourself as {ai_name} and explain how you can help with: {objective}",
                "expected_output": "A friendly introduction and a brief summary of capabilities.",
                "agent": "assistant",
            }
        }
        with open(start_task, "w") as f:
            yaml.dump(task_cfg, f)

    # 4. Hello Skill
    skills_dir = Path("./workspace/skills")
    skills_dir.mkdir(parents=True, exist_ok=True)
    hello_skill = skills_dir / "hello.md"
    if not hello_skill.exists():
        hello_skill.write_text(
            f"""---
name: "say_hello"
description: "Generates a personalized greeting."
parameters:
  name: "The name to greet"
---

```python
def execute(name="User"):
    return f"Hello {{name}}! I am {ai_name}, your new assistant focused on {objective}."
```
"""
        )


@cli.command()
@click.argument("path", default="./workspace/memory")
def index(path: str) -> None:
    """Index memory files into vector store."""
    from pathlib import Path

    try:
        from crewclaw.agent.memory import get_database, create_embedder, Chunker, VectorStore
    except ImportError as e:
        console.print(f"[red]Erro ao importar módulos: {e}[/red]")
        console.print("[yellow]Execute: pip install -e .[/yellow]")
        sys.exit(1)

    mem_dir = Path(path)
    if not mem_dir.exists():
        console.print(f"[red]Diretório não encontrado:[/red] {path}")
        return

    console.print(f"[cyan]Indexando arquivos em:[/cyan] {path}")

    # Initialize components
    db = get_database()
    embedder = create_embedder()
    vector_store = VectorStore(db)
    chunker = Chunker()

    # Index all markdown files
    indexed = 0
    for md_file in mem_dir.rglob("*.md"):
        if md_file.name.startswith("."):
            continue

        content = md_file.read_text()
        chunks = chunker.chunk_text(content, str(md_file))

        for chunk in chunks:
            embedding = embedder.embed(chunk.text)
            vector_store.insert(
                content=chunk.text,
                embedding=embedding,
                file_path=str(md_file),
                metadata={"index": chunk.index},
                chunk_index=chunk.index,
            )
            indexed += 1

    console.print(
        f"[green]Indexados {indexed} chunks de {len(list(mem_dir.rglob('*.md')))} arquivos[/green]"
    )


@cli.command()
@click.option("--path", "-p", default="./workspace/memory", help="Path to watch")
@click.option("--recursive/--no-recursive", default=True, help="Watch recursively")
def watch(path: str, recursive: bool) -> None:
    """Watch memory directory for changes and auto-index.

    This command starts a file watcher that monitors the memory
    directory for changes and automatically indexes new content.

    Example:
        crewclaw watch --path ./workspace/memory
    """
    from crewclaw.agent.watcher import FileWatcher
    from crewclaw.agent.memory import Chunker, VectorStore, create_embedder

    console.print(f"[cyan]Iniciando watcher em: {path}[/cyan]")
    console.print("[yellow]Press Ctrl+C para parar[/yellow]")

    chunker = Chunker()
    vector_store = VectorStore()
    embedder = create_embedder()

    def on_modified(file_path: str):
        """Handle file modification."""
        console.print(f"[green]Arquivo modificado: {file_path}[/green]")

        md_file = Path(file_path)
        if not md_file.exists() or md_file.suffix != ".md":
            return

        try:
            content = md_file.read_text()
            chunks = chunker.chunk_text(content, str(md_file))

            for chunk in chunks:
                embedding = embedder.embed(chunk.text)
                vector_store.insert(
                    content=chunk.text,
                    embedding=embedding,
                    file_path=str(md_file),
                    metadata={"index": chunk.index},
                    chunk_index=chunk.index,
                )
            console.print(f"[green]Indexados {len(chunks)} chunks[/green]")
        except Exception as e:
            console.print(f"[red]Erro ao indexar: {e}[/red]")

    watcher = FileWatcher(
        watch_paths=[path],
        on_modified=on_modified,
    )

    try:
        watcher.start()
        import time

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Parando watcher...[/yellow]")
        watcher.stop()
        console.print("[green]Watcher parado[/green]")


@cli.command()
def docs() -> None:
    """Open documentation."""
    docs_path = Path(__file__).parent.parent.parent / "docs" / "all.md"
    if docs_path.exists():
        console.print(docs_path.read_text())
    else:
        console.print("[yellow]Documentação não encontrada. Use: crewclaw help <topic>[/yellow]")
        console.print("Tópicos: all, memory, search, runtime, architecture")


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
