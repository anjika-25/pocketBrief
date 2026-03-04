"""
Phase 7 — Conversation Memory
Manages chat history for multi-turn conversations.
"""

import logging
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import MAX_HISTORY

logger = logging.getLogger(__name__)


class ConversationMemory:
    """Simple in-memory chat history manager."""

    def __init__(self, max_exchanges: int = MAX_HISTORY):
        self.max_exchanges = max_exchanges
        self.chat_history: list[dict[str, str]] = []

    def add_user_message(self, content: str) -> None:
        """Append a user message."""
        self.chat_history.append({"role": "user", "content": content})
        logger.debug(f"User message added. History length: {len(self.chat_history)}")

    def add_assistant_message(self, content: str) -> None:
        """Append an assistant message."""
        self.chat_history.append({"role": "assistant", "content": content})
        logger.debug(f"Assistant message added. History length: {len(self.chat_history)}")

    def get_recent_history(self, n: int | None = None) -> list[dict[str, str]]:
        """
        Return the last *n* exchanges (pairs of user + assistant messages).

        Args:
            n: Number of exchanges to return. Defaults to self.max_exchanges.

        Returns:
            List of message dicts (role, content).
        """
        n = n or self.max_exchanges
        # Each exchange = 2 messages (user + assistant)
        num_messages = n * 2
        return self.chat_history[-num_messages:] if self.chat_history else []

    def get_full_history(self) -> list[dict[str, str]]:
        """Return the entire conversation history."""
        return list(self.chat_history)

    def clear(self) -> None:
        """Reset conversation memory."""
        self.chat_history.clear()
        logger.info("Conversation memory cleared.")

    def format_history(self, n: int | None = None) -> str:
        """Format recent history into a readable string for the LLM prompt."""
        recent = self.get_recent_history(n)
        if not recent:
            return "No previous conversation."
        lines: list[str] = []
        for msg in recent:
            role = "User" if msg["role"] == "user" else "Assistant"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)


# Global singleton so the memory persists across requests in the same process
memory = ConversationMemory()
