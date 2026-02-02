from letters_project.orchestrator import Orchestrator


def test_events_are_recorded():
    orch = Orchestrator()
    letter_id = orch.create_letter(
        content="Checking event bus.",
        release_date="2099-12-31T23:59:59",
        to_address="test@example.com",
    )
    # The database should have recorded at least the creation, metadata extraction
    # and sealing events. Chrono tick isn't triggered yet.
    events = orch.db.list_events()
    event_types = [ev["event_type"] for ev in events]
    assert "letter_created" in event_types
    assert "metadata_extracted" in event_types
    assert "letter_sealed" in event_types