"""Memory search tool for querying the vector store."""

import json
from pathlib import Path
from typing import Any

from crewclaw.agent.tools.base import Tool


class MemorySearchTool(Tool):
    """Search the crewclaw memory (vector store) for relevant information."""

    def __init__(
        self,
        data_dir: Path | None = None,
    ):
        self.data_dir = data_dir or Path.cwd() / ".crewclaw"

    @property
    def name(self) -> str:
        return "memory_search"

    @property
    def description(self) -> str:
        return (
            "Search the agent's memory (vector store) for relevant context using semantic search."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "minimum": 1,
                    "maximum": 20,
                    "default": 5,
                },
                "collection": {
                    "type": "string",
                    "description": "Memory collection to search (default: 'default')",
                    "default": "default",
                },
            },
            "required": ["query"],
        }

    async def execute(self, **kwargs: Any) -> str:
        query = kwargs.get("query", "")
        limit = kwargs.get("limit", 5)
        collection = kwargs.get("collection", "default")

        if not query:
            return json.dumps({"error": "Missing required parameter: query"})

        try:
            # Import memory components
            from crewclaw.agent.memory.search import HybridSearch

            search = HybridSearch()

            results = search.search(
                query=query,
                limit=limit,
            )

            if not results:
                return json.dumps(
                    {
                        "query": query,
                        "collection": collection,
                        "results": [],
                        "message": "No relevant memories found",
                    }
                )

            return json.dumps(
                {
                    "query": query,
                    "collection": collection,
                    "results": [
                        {
                            "id": r.id,
                            "content": r.content[:500],  # Truncate long content
                            "score": r.score,
                            "source": r.metadata.get("source", "unknown")
                            if r.metadata
                            else "unknown",
                        }
                        for r in results
                    ],
                }
            )

        except ImportError as e:
            return json.dumps(
                {
                    "error": "Memory module not available",
                    "details": str(e),
                }
            )
        except Exception as e:
            return json.dumps(
                {
                    "error": f"Error searching memory: {str(e)}",
                    "query": query,
                }
            )
