"""Heartbeat and Hook management for CrewClaw."""

import asyncio
import logging
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class HookManager:
    """Manages scheduled hooks (atomic actions)."""

    def __init__(self):
        self.hooks: list[dict] = []
        self._stop_event = asyncio.Event()
        self._loop_task: Optional[asyncio.Task] = None

    def add_hook(
        self,
        name: str,
        cron_or_interval: str,
        action: str,
        target: str,
        payload: Optional[Dict] = None,
    ):
        """Add a hook to the schedule."""
        logger.info(f"Adding hook: {name} ({cron_or_interval})")

        # Simplified parsing: assume "N minutes"
        interval_seconds = 60
        if "minute" in cron_or_interval:
            try:
                interval_seconds = int(cron_or_interval.split()[0]) * 60
            except (ValueError, IndexError):
                pass

        hook = {
            "name": name,
            "interval": interval_seconds,
            "action": action,
            "target": target,
            "payload": payload,
            "last_run": 0.0,
        }
        self.hooks.append(hook)

    async def start(self):
        """Start the hook execution loop."""
        if self._loop_task:
            return

        self._loop_task = asyncio.create_task(self._loop())

    async def _loop(self):
        while not self._stop_event.is_set():
            now = time.time()
            for hook in self.hooks:
                if now - hook["last_run"] >= hook["interval"]:
                    try:
                        await self.run_hook(
                            hook["name"], hook["action"], hook["target"], hook["payload"]
                        )
                        hook["last_run"] = now
                    except Exception as e:
                        logger.error(f"Hook {hook['name']} failed: {e}")

            await asyncio.sleep(10)  # Check every 10 seconds

    def stop(self):
        self._stop_event.set()
        if self._loop_task:
            self._loop_task.cancel()

    async def run_hook(self, name: str, action: str, target: str, payload: Optional[Dict]):
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
