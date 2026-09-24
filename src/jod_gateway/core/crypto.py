import json
import os
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

NONCE_SIZE = 12
TAG_SIZE = 16
KEY_SIZE = 32


def load_or_create_master_key(path: str) -> bytes:
    key_path = Path(path)
    key_path.parent.mkdir(parents=True, exist_ok=True)

    if key_path.exists():
        return key_path.read_bytes()

    key = os.urandom(KEY_SIZE)
    key_path.write_bytes(key)
    os.chmod(key_path, 0o600)
    return key


def encrypt(plaintext: str, key: bytes) -> bytes:
    nonce = os.urandom(NONCE_SIZE)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return nonce + ciphertext


def decrypt(blob: bytes, key: bytes) -> str:
    if len(blob) < NONCE_SIZE + TAG_SIZE:
        raise InvalidTag("ciphertext too short")
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(blob[:NONCE_SIZE], blob[NONCE_SIZE:], None)
    return plaintext.decode()


def encrypt_json(obj: dict, key: bytes) -> bytes:
    return encrypt(json.dumps(obj), key)


def decrypt_json(blob: bytes, key: bytes) -> dict:
    return json.loads(decrypt(blob, key))