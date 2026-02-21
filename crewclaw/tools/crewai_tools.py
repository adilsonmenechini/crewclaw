"""CrewAI-compatible tools that wrap the crewclaw tools."""

from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel


# Args schemas first (forward reference)
class WebSearchArgs(BaseModel):
    """Arguments for web search."""

    query: str
    count: int = 5


class WebFetchArgs(BaseModel):
    """Arguments for web fetch."""

    url: str
    extract_mode: str = "markdown"
    max_chars: int = 50000


class FileReadArgs(BaseModel):
    """Arguments for file read."""

    path: str
    offset: int = 1
    limit: int | None = None


class FileWriteArgs(BaseModel):
    """Arguments for file write."""

    path: str
    content: str
    append: bool = False


class GrepArgs(BaseModel):
    """Arguments for grep."""

    pattern: str
    path: str = "."
    case_sensitive: bool = True
    whole_word: bool = False
    max_results: int = 100


class DirectoryListArgs(BaseModel):
    """Arguments for directory list."""

    path: str = "."
    recursive: bool = False
    max_depth: int = 3


class WebSearchTool(BaseTool):
    """CrewAI wrapper for web search using DuckDuckGo."""

    name: str = "web_search"
    description: str = "Search the web for information. Returns titles, URLs, and snippets."
    args_schema: Type[BaseModel] = WebSearchArgs

    def _run(self, query: str, count: int = 5) -> str:
        """Execute the web search."""
        import asyncio
        from crewclaw.tools.web import WebSearchTool as RawWebSearchTool

        async def run_search():
            tool = RawWebSearchTool(max_results=count)
            return await tool.execute(query=query)

        return asyncio.run(run_search())


class WebSearchArgs(BaseModel):
    """Arguments for web search."""

    query: str
    count: int = 5


class WebFetchTool(BaseTool):
    """CrewAI wrapper for web fetch using Readability."""

    name: str = "web_fetch"
    description: str = "Fetch a URL and extract readable content (HTML to markdown/text)."
    args_schema: Type[BaseModel] = WebFetchArgs

    def _run(self, url: str, extract_mode: str = "markdown", max_chars: int = 50000) -> str:
        """Execute the web fetch."""
        import asyncio
        from crewclaw.tools.web import WebFetchTool as RawWebFetchTool

        async def run_fetch():
            tool = RawWebFetchTool(max_chars=max_chars)
            return await tool.execute(url=url, extract_mode=extract_mode)

        return asyncio.run(run_fetch())


class WebFetchArgs(BaseModel):
    """Arguments for web fetch."""

    url: str
    extract_mode: str = "markdown"
    max_chars: int = 50000


class FileReadToolCrewAI(BaseTool):
    """CrewAI wrapper for file read."""

    name: str = "file_read"
    description: str = "Read the contents of a file."
    args_schema: Type[BaseModel] = FileReadArgs

    def _run(self, path: str, offset: int = 1, limit: int | None = None) -> str:
        """Execute the file read."""
        import asyncio
        from crewclaw.tools.file_read import FileReadTool as RawFileReadTool

        async def run_read():
            tool = RawFileReadTool()
            return await tool.execute(path=path, offset=offset, limit=limit)

        return asyncio.run(run_read())


class FileReadArgs(BaseModel):
    """Arguments for file read."""

    path: str
    offset: int = 1
    limit: int | None = None


class FileWriteToolCrewAI(BaseTool):
    """CrewAI wrapper for file write."""

    name: str = "file_write"
    description: str = "Write content to a file."
    args_schema: Type[BaseModel] = FileWriteArgs

    def _run(self, path: str, content: str, append: bool = False) -> str:
        """Execute the file write."""
        import asyncio
        from crewclaw.tools.file_write import FileWriteTool as RawFileWriteTool

        async def run_write():
            tool = RawFileWriteTool()
            return await tool.execute(path=path, content=content, append=append)

        return asyncio.run(run_write())


class FileWriteArgs(BaseModel):
    """Arguments for file write."""

    path: str
    content: str
    append: bool = False


class GrepToolCrewAI(BaseTool):
    """CrewAI wrapper for grep."""

    name: str = "grep"
    description: str = "Search for text patterns in files."
    args_schema: Type[BaseModel] = GrepArgs

    def _run(
        self,
        pattern: str,
        path: str = ".",
        case_sensitive: bool = True,
        whole_word: bool = False,
        max_results: int = 100,
    ) -> str:
        """Execute the grep."""
        import asyncio
        from crewclaw.tools.grep import GrepTool as RawGrepTool

        async def run_grep():
            tool = RawGrepTool()
            return await tool.execute(
                pattern=pattern,
                path=path,
                case_sensitive=case_sensitive,
                whole_word=whole_word,
                max_results=max_results,
            )

        return asyncio.run(run_grep())


class GrepArgs(BaseModel):
    """Arguments for grep."""

    pattern: str
    path: str = "."
    case_sensitive: bool = True
    whole_word: bool = False
    max_results: int = 100


class DirectoryListToolCrewAI(BaseTool):
    """CrewAI wrapper for directory list."""

    name: str = "directory_list"
    description: str = "List files and directories in a path."
    args_schema: Type[BaseModel] = DirectoryListArgs

    def _run(self, path: str = ".", recursive: bool = False, max_depth: int = 3) -> str:
        """Execute the directory list."""
        import asyncio
        from crewclaw.tools.directory_list import DirectoryListTool as RawDirectoryListTool

        async def run_list():
            tool = RawDirectoryListTool()
            return await tool.execute(path=path, recursive=recursive, max_depth=max_depth)

        return asyncio.run(run_list())


class MemorySearchArgs(BaseModel):
    """Arguments for memory search."""

    query: str
    limit: int = 5
    collection: str = "default"


class MemorySearchToolCrewAI(BaseTool):
    """CrewAI wrapper for memory search."""

    name: str = "memory_search"
    description: str = (
        "Search the agent's memory (vector store) for relevant context using semantic search."
    )
    args_schema: Type[BaseModel] = MemorySearchArgs

    def _run(self, query: str, limit: int = 5, collection: str = "default") -> str:
        """Execute the memory search."""
        import asyncio
        from crewclaw.tools.memory_search import MemorySearchTool as RawMemorySearchTool

        async def run_search():
            tool = RawMemorySearchTool()
            return await tool.execute(query=query, limit=limit, collection=collection)

        return asyncio.run(run_search())


class ExecArgs(BaseModel):
    """Arguments for shell execution."""

    command: str
    working_dir: str | None = None


class ExecToolCrewAI(BaseTool):
    """CrewAI wrapper for shell command execution."""

    name: str = "exec"
    description: str = "Execute a shell command and return its output. Use for running kubectl, git, python, etc."
    args_schema: Type[BaseModel] = ExecArgs

    def _run(self, command: str, working_dir: str | None = None) -> str:
        """Execute shell command."""
        import asyncio
        from crewclaw.tools.shell import ExecTool as RawExecTool

        async def run_exec():
            tool = RawExecTool(timeout=60)
            return await tool.execute(command=command, working_dir=working_dir)

        return asyncio.run(run_exec())
