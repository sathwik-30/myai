import time

from backend.security.auth import (
    create_owner_token,
    hash_token,
    verify_owner_secret
)


_SESSION_TOKEN_HASH = None
_SESSION_CREATED_AT = None

SESSION_DURATION = 60 * 60 * 24


def login_owner(secret):
    global _SESSION_TOKEN_HASH
    global _SESSION_CREATED_AT

    if not verify_owner_secret(secret):
        return None

    token = create_owner_token()

    _SESSION_TOKEN_HASH = hash_token(
        token
    )

    _SESSION_CREATED_AT = time.time()

    return token


def logout_owner():
    global _SESSION_TOKEN_HASH
    global _SESSION_CREATED_AT

    _SESSION_TOKEN_HASH = None
    _SESSION_CREATED_AT = None


def get_owner_token_hash():

    if not _SESSION_TOKEN_HASH:
        return None

    if not _SESSION_CREATED_AT:
        return None

    if (
        time.time() - _SESSION_CREATED_AT
        > SESSION_DURATION
    ):
        logout_owner()
        return None

    return _SESSION_TOKEN_HASH