"""Encryption tool used by the Guardian agent.

The production system described in the project brief uses the
``cryptography`` package's Fernet implementation for symmetric
encryption. In this environment those dependencies are unavailable,
therefore a simple XOR based cipher is used as a stand‑in. While not
cryptographically secure, it demonstrates the pattern of key
generation, encryption and decryption required by the agent logic.

Encryption keys are generated as 32 random bytes and encoded using
URL‑safe Base64 strings. The encrypted payload is also Base64
encoded. This mirrors the behaviour of the real Fernet API enough
that the Guardian agent can be switched to a true Fernet
implementation without altering its call signature.
"""

from __future__ import annotations

import base64
import os
from typing import Tuple


class EncryptionTool:
    """A simple symmetric encryption tool.

    The ``encrypt`` method returns a tuple consisting of the encrypted
    content and the Base64 encoded key used. The ``decrypt`` method
    reverses the operation when given the same key.
    """

    @staticmethod
    def generate_key() -> bytes:
        """Generate a new random 32‑byte key."""
        return os.urandom(32)

    @classmethod
    def encrypt(cls, content: str) -> Tuple[str, str]:
        """Encrypt plain text and return the cipher text and key.

        :param content: Plaintext input to be encrypted.
        :returns: A tuple ``(cipher_text, key)`` where both are
            Base64‑encoded strings.
        """
        if not isinstance(content, str):
            raise TypeError("content must be a string")
        key = cls.generate_key()
        content_bytes = content.encode("utf-8")
        key_len = len(key)
        # XOR each byte of the content with a byte of the key
        encrypted_bytes = bytearray(
            (b ^ key[i % key_len] for i, b in enumerate(content_bytes))
        )
        cipher_text = base64.urlsafe_b64encode(encrypted_bytes).decode("utf-8")
        key_b64 = base64.urlsafe_b64encode(key).decode("utf-8")
        return cipher_text, key_b64

    @classmethod
    def decrypt(cls, cipher_text: str, key: str) -> str:
        """Decrypt cipher text using the provided key.

        :param cipher_text: Base64 encoded cipher text returned from
            :meth:`encrypt`.
        :param key: Base64 encoded key returned from :meth:`encrypt`.
        :returns: The original plain text.
        """
        if not (isinstance(cipher_text, str) and isinstance(key, str)):
            raise TypeError("cipher_text and key must be strings")
        encrypted_bytes = base64.urlsafe_b64decode(cipher_text.encode("utf-8"))
        key_bytes = base64.urlsafe_b64decode(key.encode("utf-8"))
        key_len = len(key_bytes)
        decrypted_bytes = bytearray(
            (b ^ key_bytes[i % key_len] for i, b in enumerate(encrypted_bytes))
        )
        return decrypted_bytes.decode("utf-8")


__all__ = ["EncryptionTool"]