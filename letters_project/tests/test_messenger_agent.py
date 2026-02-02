from letters_project.orchestrator import Orchestrator
from letters_project.tools.email_tool import MockEmailProvider


def test_messenger_sends_email():
    orch = Orchestrator()
    # Create a letter ready now
    letter_id = orch.create_letter(
        content="Sending email test.",
        release_date="2000-01-01T00:00:00",
        to_address="recipient@example.com",
    )
    # Trigger delivery
    orch.tick()
    # The mock provider should have recorded one email
    provider = orch.email_tool.provider
    assert isinstance(provider, MockEmailProvider)
    assert len(provider.sent_messages) >= 1, "no email messages were recorded"
    msg = provider.sent_messages[0]
    # Validate fields
    assert msg["to"] == "recipient@example.com"
    assert "letter" in msg["subject"].lower()