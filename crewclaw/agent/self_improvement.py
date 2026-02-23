"""Self-improvement mechanism for CrewClaw."""

import logging
import os
from typing import List

logger = logging.getLogger(__name__)


class SelfImprovementLoop:
    """Analyzes execution logs and suggests/applies improvements."""

    def __init__(self, logs_dir: str, source_dir: str):
        self.logs_dir = logs_dir
        self.source_dir = source_dir

    async def run_analysis(self):
        """Scan logs for errors and trigger reflection."""
        logger.info("Starting Self-Improvement Analysis...")
        errors = self._scan_logs_for_errors()

        if errors:
            logger.info(f"Found {len(errors)} error patterns. Triggering reflection...")
            # Here it would call the LLM to analyze errors and propose code changes
            # For Phase 5, we provide the architectural hook
            return f"Reflection triggered for {len(errors)} errors found in logs."

        return "No errors found. System is healthy."

    def _scan_logs_for_errors(self) -> List[str]:
        """Simple log scanner for common failure patterns."""
        error_lines = []
        if not os.path.exists(self.logs_dir):
            return []

        for log_file in os.listdir(self.logs_dir):
            if log_file.endswith(".log"):
                with open(os.path.join(self.logs_dir, log_file), "r") as f:
                    for line in f:
                        if "ERROR" in line or "Exception" in line:
                            error_lines.append(line.strip())
        return error_lines[:10]  # Return first 10 for analysis
