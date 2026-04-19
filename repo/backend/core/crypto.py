import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def get_aesgcm():
    key_b64 = os.getenv("APP_AES256_KEY_B64")
    if not key_b64:
        raise ValueError("APP_AES256_KEY_B64 is required and must decode to 32 bytes")
    key = base64.b64decode(key_b64)
    if len(key) != 32:
        raise ValueError("APP_AES256_KEY_B64 must decode to 32 bytes")
    return AESGCM(key)


def encrypt_text(plaintext):
    if plaintext is None or plaintext == "":
        return ""
    aes = get_aesgcm()
    nonce = os.urandom(12)
    token = aes.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + token).decode("ascii")


def decrypt_text(ciphertext):
    if ciphertext is None or ciphertext == "":
        return ""
    raw = base64.b64decode(ciphertext)
    nonce = raw[:12]
    token = raw[12:]
    aes = get_aesgcm()
    data = aes.decrypt(nonce, token, None)
    return data.decode("utf-8")
