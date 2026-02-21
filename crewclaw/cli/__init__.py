"""CLI interface for CrewClaw."""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from ..memory import HybridSearch, get_database
from ..config import get_config
from ..config.logging import setup_logging

console = Console()


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def cli(verbose: bool) -> None:
    """CrewClaw - Local-first autonomous agents."""
    setup_logging()


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
def run(task: str, agent: str, session: str | None) -> None:
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
        from crewclaw.agents.samples import get_sample_agent
        from crewclaw.memory import get_current_session, set_session

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

        if agent == "router":
            from crewclaw.agents.samples import get_sample_agent

            router = get_sample_agent("router")

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
@click.argument("path", default="./memory")
def init(path: str) -> None:
    """Initialize memory directory."""
    from pathlib import Path

    mem_dir = Path(path)
    mem_dir.mkdir(parents=True, exist_ok=True)

    welcome = mem_dir / "welcome.md"
    if not welcome.exists():
        welcome.write_text("""# Welcome to CrewClaw

This is your local memory directory. Files here will be indexed
and available for semantic search.

## Getting Started

1. Add Markdown files to this directory
2. Run `crewclaw index` to index them
3. Use `crewclaw search <query>` to find information
""")

    console.print(f"[green]Initialized memory directory:[/green] {path}")


@cli.command()
@click.argument("path", default="./memory")
def index(path: str) -> None:
    """Index memory files into vector store."""
    from pathlib import Path

    try:
        from ..memory import get_database, create_embedder, Chunker, VectorStore
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
@click.option("--path", "-p", default="./memory", help="Path to watch")
@click.option("--recursive/--no-recursive", default=True, help="Watch recursively")
def watch(path: str, recursive: bool) -> None:
    """Watch memory directory for changes and auto-index.

    This command starts a file watcher that monitors the memory
    directory for changes and automatically indexes new content.

    Example:
        crewclaw watch --path ./memory
    """
    from ..runtime.watcher import FileWatcher
    from ..memory import Chunker, VectorStore, create_embedder

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
