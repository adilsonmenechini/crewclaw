"""Multi-channel communication bridge for CrewClaw."""

import logging
from abc import ABC, abstractmethod
from typing import Callable

logger = logging.getLogger(__name__)

class BaseChannel(ABC):
    """Abstract base class for messaging channels."""
    
    @abstractmethod
    async def send_message(self, text: str, user_id: str):
        pass

    @abstractmethod
    async def listen(self, _callback: Callable):
        pass

class TelegramChannel(BaseChannel):
    """Telegram implementation using python-telegram-bot (placeholder logic)."""
    
    def __init__(self, token: str):
        self.token = token

    async def send_message(self, text: str, user_id: str):
        logger.info(f"Sending Telegram message to {user_id}: {text[:50]}...")
        # Implementation would use telegram API here

    async def listen(self, _callback: Callable):
        logger.info("Telegram listener started (Placeholder)")
        # Implementation would start bot long-polling/webhook

class ChannelBridge:
    """Manages multiple communication channels."""
    
    def __init__(self, agent_loop):
        self.agent_loop = agent_loop
        self.channels: dict[str, BaseChannel] = {}

    def add_channel(self, name: str, channel: BaseChannel):
        self.channels[name] = channel

    async def handle_incoming(self, channel_name: str, message: str, user_id: str):
        """Route incoming messages from channels to the agent loop."""
        logger.info(f"Incoming message from {channel_name}/{user_id}: {message}")
        # result = await self.agent_loop.run(message)
        # await self.channels[channel_name].send_message(result, user_id)
