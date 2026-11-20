import base64
import hashlib
import hmac
import json
import os
import secrets
import time

DEFAULT_SECRET_KEY = "local-only-change-this-key-before-deployment-2026"
SECRET_KEY = os.getenv("HMS_SECRET_KEY", DEFAULT_SECRET_KEY)
if os.getenv("APP_ENV", "development").lower() == "production":
    if SECRET_KEY == DEFAULT_SECRET_KEY or len(SECRET_KEY) < 32:
        raise RuntimeError(
            "Set HMS_SECRET_KEY to a random value of at least 32 characters in production."
        )
TOKEN_SECONDS = 8 * 60 * 60
PASSWORD_ROUNDS = 310_000


def _encode_part(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode_part(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ROUNDS
    )
    return f"pbkdf2_sha256${PASSWORD_ROUNDS}${_encode_part(salt)}${_encode_part(digest)}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        scheme, rounds, salt_text, digest_text = stored_hash.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        expected = _decode_part(digest_text)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), _decode_part(salt_text), int(rounds)
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: int, role: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": str(user_id), "role": role, "exp": int(time.time()) + TOKEN_SECONDS}
    header_part = _encode_part(json.dumps(header, separators=(",", ":")).encode())
    payload_part = _encode_part(json.dumps(payload, separators=(",", ":")).encode())
    message = f"{header_part}.{payload_part}".encode("ascii")
    signature = hmac.new(SECRET_KEY.encode("utf-8"), message, hashlib.sha256).digest()
    return f"{header_part}.{payload_part}.{_encode_part(signature)}"


def read_access_token(token: str):
    try:
        header_part, payload_part, signature_part = token.split(".")
        message = f"{header_part}.{payload_part}".encode("ascii")
        expected = hmac.new(
            SECRET_KEY.encode("utf-8"), message, hashlib.sha256
        ).digest()
        if not hmac.compare_digest(expected, _decode_part(signature_part)):
            return None
        header = json.loads(_decode_part(header_part))
        payload = json.loads(_decode_part(payload_part))
        if header.get("alg") != "HS256" or int(payload.get("exp", 0)) <= int(time.time()):
            return None
        return payload
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None
