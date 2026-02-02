"""Database and persistence layer for the Letters to My Future Self project.

This module provides a light‑weight wrapper around SQLite for storing
letters, events and any related metadata. The database schema is
initialized on first connection and maintained throughout the lifetime
of the application. All timestamps are stored as ISO formatted strings
(e.g. ``2026-01-25T12:34:56``) to simplify comparison and human
readability.

The database file lives under ``letters_project/memory/letters.db`` by
default. When constructing a :class:`Database` you may override the
path with a custom location. The connection is created with
``check_same_thread=False`` so it can be shared across threads if
necessary, though the event bus and orchestrator are currently
synchronous.
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional


def _iso_now() -> str:
    """Return the current UTC time as an ISO formatted string.

    Although the user is in the America/Chicago timezone, we store
    timestamps in UTC to avoid ambiguities around daylight savings
    changes. Clients should convert to local time as needed.
    """
    return datetime.utcnow().replace(microsecond=0).isoformat()


class Database:
    """Simple wrapper around SQLite for letter storage.

    The database schema is created lazily on the first call to
    :func:`create_tables`. The class exposes a handful of convenience
    methods for inserting and updating letters, recording events and
    retrieving records. All operations use parameterised queries to
    protect against SQL injection. JSON blobs are used for the
    metadata and payload fields to allow flexible structures without
    migrations.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        # Determine the database location. When no explicit path is
        # provided a default file under the project directory is used.
        if db_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(base_dir, "letters.db")
        # Ensure the directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        # Use row factory so that rows behave like dictionaries
        self.connection.row_factory = sqlite3.Row
        self.create_tables()

    def create_tables(self) -> None:
        """Create the necessary tables if they do not already exist."""
        cur = self.connection.cursor()
        # Letters table stores the lifecycle of each letter. The
        # ``status`` column reflects the current state (draft, sealed,
        # scheduled, ready, delivered, archived).
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS letters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,
                metadata TEXT,
                encrypted_content TEXT,
                encryption_key TEXT,
                release_date TEXT,
                to_address TEXT,
                status TEXT,
                summary TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        # Events table stores a history of all published events. The
        # payload is stored as a JSON blob for arbitrary data.
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                letter_id INTEGER,
                timestamp TEXT,
                payload TEXT
            )
            """
        )
        self.connection.commit()

    # ------------------------------------------------------------------
    # Letter operations
    # ------------------------------------------------------------------

    def insert_letter(
        self, *, content: str, release_date: str, to_address: str, status: str = "draft"
    ) -> int:
        """Insert a new letter into the database.

        :param content: The raw letter text supplied by the user.
        :param release_date: ISO formatted date/time when the letter
            should be revealed.
        :param to_address: Email address of the recipient.
        :param status: Initial status of the letter (default ``draft``).
        :returns: The auto‑generated primary key of the new record.
        """
        now = _iso_now()
        cur = self.connection.cursor()
        cur.execute(
            """
            INSERT INTO letters (content, metadata, encrypted_content, encryption_key,
                                 release_date, to_address, status, summary,
                                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (content, json.dumps({}), None, None, release_date, to_address, status, None, now, now),
        )
        self.connection.commit()
        return cur.lastrowid

    def update_letter(
        self, letter_id: int, *, updates: Dict[str, Any]
    ) -> None:
        """Update fields on an existing letter.

        :param letter_id: Primary key of the letter to update.
        :param updates: Mapping of column names to new values. JSON
            values will be serialised automatically.
        """
        if not updates:
            return
        fields = []
        values: List[Any] = []
        for key, value in updates.items():
            if key in ("metadata", "payload"):
                # Serialise JSON columns
                value = json.dumps(value)
            fields.append(f"{key} = ?")
            values.append(value)
        # Always update the timestamp
        fields.append("updated_at = ?")
        values.append(_iso_now())
        values.append(letter_id)
        sql = f"UPDATE letters SET {', '.join(fields)} WHERE id = ?"
        cur = self.connection.cursor()
        cur.execute(sql, tuple(values))
        self.connection.commit()

    def get_letter(self, letter_id: int) -> Dict[str, Any]:
        """Retrieve a letter record as a plain dictionary."""
        cur = self.connection.cursor()
        cur.execute("SELECT * FROM letters WHERE id = ?", (letter_id,))
        row = cur.fetchone()
        if row is None:
            raise KeyError(f"Letter with id {letter_id} not found")
        # Convert JSON fields back to Python objects
        result = dict(row)
        if result.get("metadata"):
            try:
                result["metadata"] = json.loads(result["metadata"])
            except Exception:
                result["metadata"] = {}
        if result.get("summary") is None:
            result["summary"] = None
        return result

    def list_letters(self) -> List[Dict[str, Any]]:
        """Return all letters ordered by creation time."""
        cur = self.connection.cursor()
        cur.execute("SELECT * FROM letters ORDER BY created_at ASC")
        rows = cur.fetchall()
        results: List[Dict[str, Any]] = []
        for row in rows:
            result = dict(row)
            if result.get("metadata"):
                try:
                    result["metadata"] = json.loads(result["metadata"])
                except Exception:
                    result["metadata"] = {}
            results.append(result)
        return results

    # ------------------------------------------------------------------
    # Event operations
    # ------------------------------------------------------------------

    def record_event(
        self, event_type: str, letter_id: Optional[int], payload: Optional[Dict[str, Any]]
    ) -> None:
        """Persist an event to the database.

        :param event_type: Name of the event (e.g. ``letter_created``).
        :param letter_id: Associated letter ID, if any.
        :param payload: Arbitrary JSON serialisable payload.
        """
        cur = self.connection.cursor()
        cur.execute(
            """
            INSERT INTO events (event_type, letter_id, timestamp, payload)
            VALUES (?, ?, ?, ?)
            """,
            (
                event_type,
                letter_id,
                _iso_now(),
                json.dumps(payload or {}),
            ),
        )
        self.connection.commit()

    def list_events(self) -> List[Dict[str, Any]]:
        """Return all recorded events."""
        cur = self.connection.cursor()
        cur.execute("SELECT * FROM events ORDER BY id ASC")
        rows = cur.fetchall()
        return [dict(row) for row in rows]


__all__ = ["Database"]