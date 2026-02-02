"""Archivist Agent – summarises and archives delivered letters.

When a letter is delivered the archivist consolidates the memory by
creating a summary of the original content and updating the status to
``archived``. After archiving the letter it emits a
``letter_archived`` event. This stage mimics long‑term memory
consolidation and cleanup of transient state.
"""

from __future__ import annotations

from .base import BaseAgent
from ..events.event_bus import EventBus, Event


class ArchivistAgent(BaseAgent):
    name = "archivist"
    subscriptions = ["letter_delivered"]

    def handle_event(self, event: Event, bus: EventBus) -> None:
        if event.event_type != "letter_delivered" or event.letter_id is None:
            return
        letter = self.db.get_letter(event.letter_id)
        content = letter.get("content", "")
        # Generate a summary of the letter content
        try:
            summary = self.llm.summarise(content)
        except Exception:
            # Best-effort AI: never block delivery due to LLM outages
            summary = (content.strip()[:57] + "...") if len(content.strip()) > 60 else content.strip()
        # Update the letter record
        self.db.update_letter(letter["id"], updates={"summary": summary, "status": "archived"})
        # Publish an event to signal archival
        bus.publish("letter_archived", event.letter_id, payload={"summary": summary})


__all__ = ["ArchivistAgent"]