import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SECRET_PATH = PROJECT_ROOT / "backend/auth/data/.auth_secret"

def _load_secret() -> bytes:
    configured = os.getenv("MEDHA_AUTH_SECRET")
    if configured:
        return configured.encode()
    SECRET_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        value = SECRET_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        value = ""
    if not value:
        value = secrets.token_urlsafe(64)
        SECRET_PATH.write_text(value, encoding="utf-8")
        try:
            os.chmod(SECRET_PATH, 0o600)
        except OSError:
            pass
    return value.encode()

SECRET = _load_secret()
TOKEN_TTL = 60 * 60 * 24 * 7

def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 180000)
    return "pbkdf2_sha256$180000$%s$%s" % (_b64(salt), _b64(digest))

def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, rounds, salt, expected = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), _unb64(salt), int(rounds))
        return hmac.compare_digest(_b64(digest), expected)
    except (ValueError, TypeError):
        return False

def create_token(user_id: int, username: str, role: str = "user") -> str:
    now = int(time.time())
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64(json.dumps({
        "sub": user_id, "username": username, "role": role,
        "iat": now, "exp": now + TOKEN_TTL,
    }, separators=(",", ":")).encode())
    signature = _b64(hmac.new(SECRET, (header + "." + payload).encode(), hashlib.sha256).digest())
    return header + "." + payload + "." + signature

def decode_token(token: str) -> Dict[str, Any] | None:
    try:
        header, payload, signature = token.split(".")
        expected = _b64(hmac.new(SECRET, (header + "." + payload).encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            return None
        data = json.loads(_unb64(payload))
        if int(data["exp"]) < int(time.time()):
            return None
        return data
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None
