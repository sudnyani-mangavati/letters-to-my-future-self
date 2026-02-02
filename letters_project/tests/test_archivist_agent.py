from letters_project.orchestrator import Orchestrator


def test_archivist_creates_summary():
    orch = Orchestrator()
    letter_id = orch.create_letter(
        content="This is a long letter about my experiences and what I've learned over the years.",
        release_date="2000-01-01T00:00:00",
        to_address="archive@example.com",
    )
    orch.tick()
    letter = orch.get_letter(letter_id)
    summary = letter.get("summary")
    assert summary is not None and summary != "", "summary should not be empty"
    # The summary should not be identical to the full content if it's long
    if len(letter["content"]) > 60:
        assert summary != letter["content"], "summary should be a truncated version"