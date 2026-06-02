"""Background scheduler for automatic letter delivery.

Replaces the manual ``tick`` UI that was previously used to trigger
time-based checks. The scheduler runs a daemon thread that
periodically calls the orchestrator's ``tick()`` method, which in
turn fires the Chrono agent to evaluate whether any sealed letters
have reached their release date.

The thread is intentionally a daemon so it dies automatically when
the main process exits. All exceptions inside the loop are caught
and logged to prevent the scheduler from silently crashing.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .orchestrator import Orchestrator

logger = logging.getLogger(__name__)


class Scheduler:
    """Periodically triggers ``orchestrator.tick()`` in a background thread."""

    def __init__(self, orchestrator: Orchestrator, interval: int = 30) -> None:
        """
        :param orchestrator: The application orchestrator instance.
        :param interval: Seconds between each tick (default 30).
        """
        self.orch = orchestrator
        self.interval = interval
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Scheduler started (interval=%ds)", self.interval)

    def _run(self) -> None:
        """Main loop – runs until stop() is called or the process exits."""
        while not self._stop_event.is_set():
            try:
                self.orch.tick()
            except Exception:
                logger.exception("Scheduler tick failed")
            self._stop_event.wait(self.interval)

    def stop(self) -> None:
        """Signal the background thread to stop."""
        self._stop_event.set()
        logger.info("Scheduler stopped")

    @property
    def running(self) -> bool:
        return self._thread.is_alive() and not self._stop_event.is_set()


__all__ = ["Scheduler"]