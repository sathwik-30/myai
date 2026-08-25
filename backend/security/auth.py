import os
import secrets
import hashlib
import hmac


OWNER_NAME = "Sathwik"

_OWNER_SECRET = os.getenv(
    "MEDHA_OWNER_SECRET"
)


def _get_owner_secret():
    if not _OWNER_SECRET:
        raise RuntimeError(
            "MEDHA_OWNER_SECRET is not configured."
        )

    return _OWNER_SECRET


def create_owner_token():
    """
    Create a cryptographically random owner session token.
    """

    return secrets.token_urlsafe(32)


def hash_token(token):
    """
    Hash a token before storing/comparing it.
    """

    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def verify_owner_secret(secret):
    """
    Verify the owner's secret.
    """

    expected = _get_owner_secret()

    return hmac.compare_digest(
        secret,
        expected
    )


def verify_owner_token(
    token,
    stored_hash
):
    """
    Verify an authenticated owner token.
    """

    if not token or not stored_hash:
        return False

    token_hash = hash_token(token)

    return hmac.compare_digest(
        token_hash,
        stored_hash
    )