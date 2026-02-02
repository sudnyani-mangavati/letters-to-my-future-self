"""Base class for all agents.

Agents receive events from the orchestrator and perform reasoning and
actions based on their role. Subclasses should implement
``subscriptions`` to declare which event types they handle and
override ``handle_event`` to perform work when those events arrive.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from ..events.event_bus import Event
from ..memory.db import Database
from ..tools.llm_provider import LLMProvider
from ..tools.encryption_tool import EncryptionTool
from ..tools.email_tool import EmailTool


class BaseAgent:
    """Abstract base agent class.

    Each agent is given access to the shared database, the event bus
    (provided separately by the orchestrator), the LLM provider and
    optionally any specialised tools it may need. Subclasses must
    define a ``name`` and a list of ``subscriptions`` enumerating the
    event types they handle. If no subscription list is provided the
    agent will receive no events.
    """

    name: str = "base"
    subscriptions: List[str] = []

    def __init__(
        self,
        db: Database,
        llm: LLMProvider,
        encryption_tool: Optional[EncryptionTool] = None,
        email_tool: Optional[EmailTool] = None,
    ) -> None:
        self.db = db
        self.llm = llm
        self.encryption_tool = encryption_tool
        self.email_tool = email_tool

    def handle_event(self, event: Event, bus) -> None:
        """Handle an incoming event.

        Subclasses should override this method. Any new events
        generated should be published on the provided event bus.
        """
        raise NotImplementedError


__all__ = ["BaseAgent"]