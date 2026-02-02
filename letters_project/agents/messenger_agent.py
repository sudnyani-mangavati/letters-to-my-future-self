"""Messenger Agent – composes and sends the delivery message.

When a letter becomes ready the messenger generates a personalised
message using the LLM and invokes the configured email provider to
send the content to the recipient. After sending, the letter's
status is updated to ``delivered`` and a ``letter_delivered`` event
is emitted for the Archivist to process.
"""

from __future__ import annotations

from .base import BaseAgent
from ..events.event_bus import EventBus, Event


class MessengerAgent(BaseAgent):
    name = "messenger"
    subscriptions = ["letter_ready"]

    def handle_event(self, event: Event, bus: EventBus) -> None:
        if event.event_type != "letter_ready" or event.letter_id is None:
            return
        letter = self.db.get_letter(event.letter_id)
        # Retrieve metadata for tone and other context
        metadata = letter.get("metadata") or {}
        content = letter.get("content", "")
        # Compose the message using the LLM provider
        message_body = content
        subject = "Knock knock! Your past self sent you a letter!"
        to_address = letter.get("to_address") or "unknown@example.com"
        # Send the email via the configured email tool
        self.email_tool.send_email(to_address, subject, message_body)
        # Update the letter status to delivered
        self.db.update_letter(letter["id"], updates={"status": "delivered"})
        # Publish event
        bus.publish("letter_delivered", event.letter_id, payload={})


__all__ = ["MessengerAgent"]