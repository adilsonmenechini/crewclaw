"""Memory Feedback Loop - Emulates RNN behavior for agents.

This module implements the "Write Reflexive" process from the documentation:
1. Agent completes a task
2. Runtime asks LLM: "Was there anything new and important?"
3. LLM generates a summary
4. Summary is written to Markdown and indexed in SQLite
5. Next time agent runs, this summary "feeds" its mind
"""

from datetime import datetime
from pathlib import Path

from crewclaw.config import get_config
from crewclaw.config.logging import get_logger
from crewclaw.providers.embedder import create_embedder
from crewclaw.agent.memory.markdown import MemoryFile, MemoryOrganizer
from crewclaw.agent.memory.vectorstore import VectorStore

logger = get_logger(__name__)


class MemoryFeedbackLoop:
    """
    Memory Feedback Loop - Simulates RNN recurrence.

    After each task, this loop:
    1. Asks the LLM to summarize important information
    2. Saves the summary to Markdown
    3. Indexes it in SQLite for future retrieval
    """

    def __init__(
        self,
        memory_dir: str | None = None,
        enabled: bool | None = None,
    ):
        """Initialize the memory feedback loop.

        Args:
            memory_dir: Directory to store memory files.
            enabled: Whether feedback loop is enabled.
        """
        config = get_config()
        self.enabled = (
            enabled if enabled is not None else config.get("memory_feedback.enabled", True)
        )
        self.memory_dir = Path(memory_dir or config.get("project.memory_dir", "./workspace/memory"))
        self.organizer = MemoryOrganizer(str(self.memory_dir))

        self.vector_store = VectorStore()
        self.embedder = create_embedder()

        self.min_importance = config.get("memory_feedback.min_importance", 0.7)
        self.max_memories_per_session = config.get("memory_feedback.max_memories", 5)

    async def after_task(
        self,
        task_description: str,
        task_result: str,
        llm,
    ) -> list[str]:
        """
        Process task result and extract important memories.

        Args:
            task_description: Original task description.
            task_result: Result from the task execution.
            llm: LLM instance to generate summaries.

        Returns:
            List of memory IDs created.
        """
        if not self.enabled:
            logger.debug("Memory feedback loop disabled, skipping")
            return []

        logger.info("Running memory feedback loop...")

        # Build prompt to extract important information
        prompt = self._build_extraction_prompt(task_description, task_result)

        try:
            # Ask LLM to extract important information
            summary = await self._generate_summary(prompt, llm)

            if not summary or len(summary.strip()) < 20:
                logger.debug("No important information to save")
                return []

            # Save to memory
            memory_ids = await self._save_memory(task_description, summary)

            logger.info(f"Memory feedback loop complete: {len(memory_ids)} memories saved")
            return memory_ids

        except Exception as e:
            logger.error(f"Memory feedback loop failed: {e}")
            return []

    def _build_extraction_prompt(self, task: str, result: str) -> str:
        """Build prompt for extracting important information."""
        return f"""You are a memory consolidation system. Analyze the following task and its result.
        
Task: {task}

Result: {result}

Extract any important facts, preferences, or information that should be remembered for future interactions.
Focus on:
- User preferences mentioned
- Important facts or decisions
- Context that might be useful later

Respond with a concise summary (2-4 sentences) of the most important information.
If nothing important, respond with just: NOTHING_IMPORTANT"""

    async def _generate_summary(self, prompt: str, llm) -> str:
        """Generate summary using LLM."""
        try:
            # Try async call
            response = await llm.agenerate([{"role": "user", "content": prompt}])
            text = response.generations[0][0].text
        except Exception:
            try:
                # Fallback to sync
                response = llm.generate([{"role": "user", "content": prompt}])
                text = response.generations[0][0].text
            except Exception as e:
                logger.warning(f"LLM call failed: {e}")
                return ""

        if "NOTHING_IMPORTANT" in text.upper():
            return ""

        return text.strip()

    async def _save_memory(self, task: str, summary: str) -> list[str]:
        """Save memory to Markdown and index in SQLite."""
        memory_ids = []

        # Generate filename based on task
        safe_task = "".join(c for c in task[:30] if c.isalnum() or c in " -_").strip()
        safe_task = safe_task.replace(" ", "_")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"feedback_{timestamp}_{safe_task}.md"

        # Get path for today
        date_path = self.organizer.get_path()
        file_path = date_path / filename

        # Write to Markdown with frontmatter
        memory_file = MemoryFile(str(file_path))
        metadata = {
            "type": "feedback_loop",
            "task": task,
            "created_at": datetime.now().isoformat(),
            "importance": "high",
        }
        memory_file.write(summary, metadata)

        logger.debug(f"Saved memory to {file_path}")
        memory_ids.append(str(file_path))

        # Index in SQLite
        try:
            embedding = self.embedder.embed(summary)
            self.vector_store.insert(
                content=summary,
                embedding=embedding,
                file_path=str(file_path),
                metadata={
                    "type": "feedback_loop",
                    "task": task,
                    "source": "memory_feedback_loop",
                },
            )
            logger.debug("Indexed memory in vector store")
        except Exception as e:
            logger.warning(f"Failed to index memory: {e}")

        return memory_ids


class ConsolidationHook:
    """
    Hook system for memory consolidation.

    Allows registering callbacks that run after task completion
    for memory consolidation and other post-processing.
    """

    def __init__(self):
        self._hooks: list[callable] = []

    def register(self, callback: callable) -> None:
        """Register a callback to run after task completion.

        Args:
            callback: Async function that takes (task_description, task_result, llm)
        """
        self._hooks.append(callback)
        logger.debug(f"Registered consolidation hook: {callback.__name__}")

    def unregister(self, callback: callable) -> None:
        """Unregister a callback.

        Args:
            callback: Callback to remove.
        """
        if callback in self._hooks:
            self._hooks.remove(callback)

    async def run_hooks(
        self,
        task_description: str,
        task_result: str,
        llm,
    ) -> None:
        """Run all registered hooks.

        Args:
            task_description: Original task description.
            task_result: Task result.
            llm: LLM instance.
        """
        for hook in self._hooks:
            try:
                await hook(task_description, task_result, llm)
            except Exception as e:
                logger.error(f"Hook {hook.__name__} failed: {e}")


# Global instances
_feedback_loop: MemoryFeedbackLoop | None = None
_consolidation_hook: ConsolidationHook | None = None


def get_feedback_loop() -> MemoryFeedbackLoop:
    """Get global MemoryFeedbackLoop instance."""
    global _feedback_loop
    if _feedback_loop is None:
        _feedback_loop = MemoryFeedbackLoop()
    return _feedback_loop


def get_consolidation_hook() -> ConsolidationHook:
    """Get global ConsolidationHook instance."""
    global _consolidation_hook
    if _consolidation_hook is None:
        _consolidation_hook = ConsolidationHook()
    return _consolidation_hook
