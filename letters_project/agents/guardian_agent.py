"""Guardian Agent – oversees security and encryption policy.

When the curator has extracted metadata, the guardian decides if
encryption is needed and, if so, encrypts the letter using the
EncryptionTool. It then updates the letter status to ``sealed`` and
publishes a ``letter_sealed`` event so that the Chrono agent can
monitor for its release.
"""

from __future__ import annotations

from typing import Any, Dict

from .base import BaseAgent
from ..events.event_bus import EventBus, Event


class GuardianAgent(BaseAgent):
    name = "guardian"
    subscriptions = ["metadata_extracted"]

    def handle_event(self, event: Event, bus: EventBus) -> None:
        if event.event_type != "metadata_extracted" or event.letter_id is None:
            return
        # Fetch the letter from the database
        letter = self.db.get_letter(event.letter_id)
        content = letter.get("content")
        # Decide on encryption strategy based on metadata; always encrypt
        # in this mock implementation.
        encrypted_content, key = self.encryption_tool.encrypt(content)
        # Update the letter record with encrypted content and key. Do not
        # erase the original content so the archivist can summarise it.
        updates: Dict[str, Any] = {
            "encrypted_content": encrypted_content,
            "encryption_key": key,
            "status": "sealed",
        }
        self.db.update_letter(letter["id"], updates=updates)
        # Notify other agents that the letter has been sealed
        bus.publish("letter_sealed", event.letter_id, payload={})


__all__ = ["GuardianAgent"]