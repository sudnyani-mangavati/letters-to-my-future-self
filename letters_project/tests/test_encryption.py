from letters_project.tools.encryption_tool import EncryptionTool


def test_encryption_roundtrip():
    tool = EncryptionTool()
    message = "This is a secret message."
    cipher, key = tool.encrypt(message)
    decrypted = tool.decrypt(cipher, key)
    assert decrypted == message, "encryption/decryption roundtrip failed"