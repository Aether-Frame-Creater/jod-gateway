import stat

import pytest
from cryptography.exceptions import InvalidTag

from jod_gateway.core.crypto import (
    decrypt,
    decrypt_json,
    encrypt,
    encrypt_json,
    load_or_create_master_key,
)


def test_roundtrip(tmp_path) -> None:
    key = load_or_create_master_key(str(tmp_path / "master.key"))
    blob = encrypt("hello sesame", key)
    assert isinstance(blob, bytes)
    assert decrypt(blob, key) == "hello sesame"


def test_json_roundtrip() -> None:
    key = b"k" * 32
    obj = {"access_token": "abc", "nested": {"a": 1}}
    assert decrypt_json(encrypt_json(obj, key), key) == obj


def test_tamper_detected() -> None:
    key = b"k" * 32
    blob = bytearray(encrypt("secret", key))
    blob[5] ^= 0xFF
    with pytest.raises(InvalidTag):
        decrypt(bytes(blob), key)


def test_master_key_creation_perms(tmp_path) -> None:
    path = str(tmp_path / "keys" / "master.key")
    key = load_or_create_master_key(path)
    assert len(key) == 32
    mode = stat.S_IMODE(tmp_path.joinpath("keys", "master.key").stat().st_mode)
    assert mode == 0o600

    again = load_or_create_master_key(path)
    assert again == key