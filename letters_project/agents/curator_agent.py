"""Curator Agent – responsible for interpreting raw letters.

Upon receiving a ``letter_created`` event, the curator uses the
language model to extract emotional tone and any other metadata from
the letter content. This metadata is stored in the letters table and
a ``metadata_extracted`` event is published so that the Guardian
agent can apply the appropriate security policy.
"""

from __future__ import annotations

from typing import Dict

from .base import BaseAgent
from ..events.event_bus import EventBus, Event


class CuratorAgent(BaseAgent):
    name = "curator"
    subscriptions = ["letter_created"]

    def handle_event(self, event: Event, bus: EventBus) -> None:
        # Only handle events we subscribe to
        if event.event_type != "letter_created" or event.letter_id is None:
            return
        letter = self.db.get_letter(event.letter_id)
        content = letter.get("content", "")
        # Use LLM to classify the emotional tone of the letter
        tone = self.llm.classify_emotion(content)
        metadata: Dict[str, str] = {"tone": tone}
        # Store metadata back to the database
        self.db.update_letter(letter["id"], updates={"metadata": metadata})
        # Emit an event to signal metadata extraction
        bus.publish("metadata_extracted", event.letter_id, payload={"metadata": metadata})


__all__ = ["CuratorAgent"]