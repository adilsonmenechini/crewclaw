"""ReAct Runtime - Autonomous execution loop."""

from typing import Callable

from crewai import Agent

from ..config import get_config
from ..config.logging import get_logger

logger = get_logger(__name__)


class ReActRuntime:
    """ReAct loop executor for autonomous agent execution."""

    def __init__(self, agent: Agent):
        """Initialize runtime.

        Args:
            agent: CrewAI agent to execute.
        """
        self.agent = agent
        config = get_config()

        self.max_iterations = config.get("runtime.max_iterations", 20)
        self.max_execution_time = config.get("runtime.max_execution_time", 300)
        self.max_retry_limit = config.get("runtime.max_retry_limit", 2)
        self.watchdog_enabled = config.get("runtime.watchdog_enabled", True)
        self.watchdog_threshold = config.get("runtime.watchdog_threshold", 3)

        self._action_history: list[dict] = []

    def execute(
        self,
        task: str,
        callbacks: list[Callable] | None = None,
    ) -> str:
        """Execute task using ReAct loop.

        Args:
            task: Task description.
            callbacks: List of callbacks for each step.

        Returns:
            Final result.
        """
        logger.info(f"Starting ReAct execution for task: {task[:50]}...")

        self._action_history = []
        iterations = 0
        last_action = None
        action_count = {}

        while iterations < self.max_iterations:
            iterations += 1

            # Execute step
            try:
                result = self.agent.execute_task(task)

                # Check for completion
                if self._is_complete(result):
                    logger.info(f"Task completed in {iterations} iterations")
                    return result

            except Exception as e:
                logger.warning(f"Error in iteration {iterations}: {e}")

                # Self-correction: retry with modified approach
                if iterations < self.max_iterations:
                    task = self._modify_task(task, str(e))
                    continue
                else:
                    raise

            # Watchdog: detect infinite loops
            if self.watchdog_enabled:
                if self._detect_loop(action_count, last_action):
                    logger.warning("Watchdog triggered: possible infinite loop")
                    raise RuntimeError("Watchdog detected potential infinite loop")

            # Run callbacks
            if callbacks:
                for callback in callbacks:
                    try:
                        callback(iterations, self._action_history)
                    except Exception as e:
                        logger.warning(f"Callback error: {e}")

        logger.warning(f"Max iterations ({self.max_iterations}) reached")
        return "Task did not complete within iteration limit"

    def _is_complete(self, result: str) -> bool:
        """Check if result indicates task completion."""
        if not result:
            return False

        # Check for completion indicators
        completion_indicators = [
            "completed",
            "finished",
            "done",
            "success",
            "result:",
        ]

        result_lower = result.lower()
        return any(indicator in result_lower for indicator in completion_indicators)

    def _detect_loop(self, action_count: dict[str, int], last_action: str | None) -> bool:
        """Detect if agent is in a loop.

        Args:
            action_count: Count of repeated actions.
            last_action: Last action performed.

        Returns:
            True if loop detected.
        """
        if last_action and last_action in action_count:
            action_count[last_action] += 1
            return action_count[last_action] >= self.watchdog_threshold

        action_count[last_action] = 1
        return False

    def _modify_task(self, task: str, error: str) -> str:
        """Modify task based on error for self-correction.

        Args:
            task: Original task.
            error: Error message.

        Returns:
            Modified task.
        """
        return f"{task}\n\nNote: Previous attempt failed with error: {error}. Please try a different approach."
