from letters_project.orchestrator import Orchestrator


def test_letter_creation_sealed_status():
    orch = Orchestrator()
    # Use a far future date so the letter does not become ready immediately
    letter_id = orch.create_letter(
        content="Dear me, stay strong and happy.",
        release_date="2099-01-01T00:00:00",
        to_address="user@example.com",
    )
    letter = orch.get_letter(letter_id)
    # After creation and event processing the letter should be sealed
    assert letter["status"] == "sealed", f"expected sealed status, got {letter['status']}"
    # Metadata should have been extracted
    assert letter["metadata"].get("tone") in {"positive", "neutral", "negative"}
    # Encrypted content and key should be present
    assert letter["encrypted_content"] is not None
    assert letter["encryption_key"] is not None