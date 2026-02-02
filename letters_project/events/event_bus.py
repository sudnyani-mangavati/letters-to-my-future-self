"""Event bus implementation for the Letters to My Future Self project.

The event bus provides an in‑process messaging layer for coordinating
the autonomous agents. Events are published by agents or the
orchestrator and subsequently dispatched to subscribers via the
orchestrator. Every published event is also persisted to the database
for auditing and debugging purposes.

The queue is implemented as a simple list. This suffices for the
synchronous execution model used here. Should concurrency be
introduced, the queue can be replaced with ``queue.Queue`` or an
``asyncio.Queue`` without affecting the interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..memory.db import Database


@dataclass
class Event:
    """Lightweight structure representing a bus event."""

    event_type: str
    letter_id: Optional[int]
    payload: Dict[str, Any]


class EventBus:
    """In memory event bus with persistence back to the database."""

    def __init__(self, db: Database) -> None:
        self.db = db
        self._queue: List[Event] = []

    def publish(self, event_type: str, letter_id: Optional[int], payload: Optional[Dict[str, Any]] = None) -> None:
        """Publish a new event and persist it.

        :param event_type: Name of the event to publish.
        :param letter_id: Identifier of the related letter or ``None``.
        :param payload: Arbitrary metadata associated with the event.
        """
        event = Event(event_type=event_type, letter_id=letter_id, payload=payload or {})
        # Append to in memory queue for immediate dispatch
        self._queue.append(event)
        # Persist to the database
        self.db.record_event(event_type, letter_id, payload)

    def get_next_event(self) -> Optional[Event]:
        """Retrieve the next event from the queue, if any."""
        if not self._queue:
            return None
        return self._queue.pop(0)

    def pending(self) -> int:
        """Return the number of events currently waiting to be dispatched."""
        return len(self._queue)

    def clear(self) -> None:
        """Clear any queued events. Primarily used in tests."""
        self._queue.clear()


__all__ = ["EventBus", "Event"]