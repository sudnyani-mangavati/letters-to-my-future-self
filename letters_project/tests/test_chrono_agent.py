from letters_project.orchestrator import Orchestrator


def test_chrono_triggers_delivery_and_archiving():
    orch = Orchestrator()
    # Create a letter scheduled in the past so it's immediately ready
    letter_id = orch.create_letter(
        content="I hope you are thriving.",
        release_date="2000-01-01T00:00:00",
        to_address="future@example.com",
    )
    # Advance time – this should mark the letter ready, send it and archive it
    orch.tick()
    letter = orch.get_letter(letter_id)
    # After tick processing the letter should be archived
    assert letter["status"] == "archived", f"expected archived, got {letter['status']}"
    # The summary should be non‑empty
    assert letter["summary"], "archivist should have summarised the letter"