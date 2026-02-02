"""Command‑line interface for interacting with the Letters system.

The CLI provides a simple wrapper around the orchestrator allowing
users to create letters, schedule them, query their status and
advance time. It is designed for local execution and testability.

Example usage:

.. code-block:: bash

    python -m letters_project.cli create --content "Hello future" --date "2026-02-01T12:00:00" --to user@example.com
    python -m letters_project.cli tick
    python -m letters_project.cli status --id 1
"""

from __future__ import annotations

import argparse
import sys
from typing import Any, Dict

from .orchestrator import Orchestrator


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Letters to My Future Self CLI",
        prog="letters",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new letter")
    create_parser.add_argument("--content", required=True, help="The body of the letter")
    create_parser.add_argument(
        "--date", required=True, help="ISO formatted date/time for when the letter should be delivered"
    )
    create_parser.add_argument(
        "--to", required=True, help="Email address of the intended recipient"
    )

    # Schedule command
    schedule_parser = subparsers.add_parser("schedule", help="Schedule an existing letter")
    schedule_parser.add_argument("--id", type=int, required=True, help="ID of the letter to schedule")
    schedule_parser.add_argument(
        "--date", required=True, help="New ISO formatted date/time for delivery"
    )

    # Status command
    status_parser = subparsers.add_parser("status", help="Show status of a letter")
    status_parser.add_argument("--id", type=int, required=True, help="ID of the letter")

    # List command
    subparsers.add_parser("list", help="List all letters")

    # Tick command
    subparsers.add_parser("tick", help="Advance time and process any ready letters")

    return parser


def main(argv: Any = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    orch = Orchestrator()
    if args.command == "create":
        letter_id = orch.create_letter(args.content, args.date, args.to)
        print(f"Created letter with ID {letter_id}")
    elif args.command == "schedule":
        orch.schedule_letter(args.id, args.date)
        print(f"Letter {args.id} rescheduled for {args.date}")
    elif args.command == "status":
        letter = orch.get_letter(args.id)
        print(letter)
    elif args.command == "list":
        letters = orch.list_letters()
        for ltr in letters:
            print(ltr)
    elif args.command == "tick":
        orch.tick()
        print("Tick processed")
    else:
        parser.print_help()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())