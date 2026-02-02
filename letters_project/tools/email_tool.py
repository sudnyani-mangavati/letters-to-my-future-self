"""Email sending abstraction used by the Messenger agent.

The production implementation would integrate with SendGrid or an SMTP
relay via the ``send_email`` method. Here we provide a simple
interface and a mock provider so that tests do not depend on
external services. Providers should inherit from
``BaseEmailProvider`` and implement ``send_email``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Optional


class BaseEmailProvider:
    """Abstract base class for email providers."""

    def send_email(self, to_address: str, subject: str, body: str) -> Dict[str, str]:
        raise NotImplementedError


class MockEmailProvider(BaseEmailProvider):
    """A provider that simulates sending email by recording messages."""

    def __init__(self) -> None:
        self.sent_messages: list[Dict[str, str]] = []

    def send_email(self, to_address: str, subject: str, body: str) -> Dict[str, str]:
        message = {"to": to_address, "subject": subject, "body": body}
        self.sent_messages.append(message)

        # Persist mock emails for debugging/demo
        log_path = os.environ.get("MOCK_EMAIL_LOG", "mock_emails.jsonl")
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"{message}\n")
        except Exception:
            # Don't fail the pipeline if logging fails
            pass

        return {"status": "sent", "message": "Email sent (mock)"}



class SMTPProvider(BaseEmailProvider):
    """A simple SMTP provider used if no SendGrid key is configured.

    This provider uses the built‑in ``smtplib`` module to send an
    email. It will only be used if environment variables for a real
    email server are provided. In most development scenarios the
    ``MockEmailProvider`` should be sufficient.
    """

    def __init__(self, host: str, port: int, username: Optional[str] = None, password: Optional[str] = None) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password

    def send_email(self, to_address: str, subject: str, body: str) -> Dict[str, str]:
        import smtplib
        from email.mime.text import MIMEText

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self.username if self.username else "no‑reply@example.com"
        msg["To"] = to_address
        with smtplib.SMTP(self.host, self.port) as server:
            try:
                if self.username and self.password:
                    server.starttls()
                    server.login(self.username, self.password)
                server.sendmail(msg["From"], [to_address], msg.as_string())
                return {"status": "sent", "message": "Email sent via SMTP"}
            except Exception as ex:
                return {"status": "error", "message": str(ex)}


class EmailTool:
    """Facade for sending emails through a configured provider."""

    def __init__(self, provider: Optional[BaseEmailProvider] = None) -> None:
        # Choose provider based on environment variables. Priority:
        # 1. SendGrid API key (not implemented here)
        # 2. SMTP details
        # 3. Mock provider
        if provider is not None:
            self.provider = provider
        else:
            smtp_host = os.environ.get("SMTP_HOST")
            smtp_port = os.environ.get("SMTP_PORT")
            smtp_user = os.environ.get("SMTP_USER")
            smtp_pass = os.environ.get("SMTP_PASS")
            if smtp_host and smtp_port:
                try:
                    port_int = int(smtp_port)
                except ValueError:
                    port_int = 25
                self.provider = SMTPProvider(smtp_host, port_int, smtp_user, smtp_pass)
            else:
                self.provider = MockEmailProvider()

    def send_email(self, to_address: str, subject: str, body: str) -> Dict[str, str]:
        """Send an email using the configured provider."""
        return self.provider.send_email(to_address, subject, body)


__all__ = [
    "BaseEmailProvider",
    "MockEmailProvider",
    "SMTPProvider",
    "EmailTool",
]