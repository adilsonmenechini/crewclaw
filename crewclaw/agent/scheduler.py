"""Heartbeat and Hook management for CrewClaw."""

import asyncio
import logging
import schedule
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class HookManager:
    """Manages scheduled hooks (atomic actions)."""
    
    def __init__(self):
        self.hooks = []
        self._stop_event = asyncio.Event()

    def add_hook(self, name: str, cron_or_interval: str, action: str, target: str, payload: Optional[Dict] = None):
        """Add a hook to the schedule."""
        logger.info(f"Adding hook: {name} ({cron_or_interval})")
        # Simplified interval parsing for demonstration (real implementation would use croniter or similar)
        if "minute" in cron_or_interval:
            interval = int(cron_or_interval.split()[0])
            schedule.every(interval).minutes.do(self.run_hook, name, action, target, payload)
        
    def run_hook(self, name: str, action: str, target: str, payload: Optional[Dict]):
        """Execute a single hook action."""
        logger.info(f"Executing hook {name} (Action: {action})")
        if action == "shell":
            import subprocess
            subprocess.run(target, shell=True)
        elif action == "webhook":
            import requests
            requests.post(target, json=payload or {})
        # More actions can be added here

class HeartbeatManager:
    """Manages proactive agent heartbeat."""
    
    def __init__(self, agent_loop):
        self.agent_loop = agent_loop
        self._task = None

    async def start(self, interval_seconds: int):
        """Start the heartbeat loop."""
        logger.info(f"Starting Heartbeat (every {interval_seconds}s)")
        while True:
            await asyncio.sleep(interval_seconds)
            logger.info("Heartbeat wake up: Running proactive maintenance")
            # In a real implementation, this would trigger a specific agent task
            # await self.agent_loop.run_task("Perform self-maintenance and status update")

    def stop(self):
        if self._task:
            self._task.cancel()
