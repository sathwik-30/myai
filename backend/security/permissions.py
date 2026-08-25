from fastapi import Header, HTTPException

from backend.security.auth import (
    verify_owner_token
)


def require_owner(
    x_medha_owner_token: str | None = Header(
        default=None
    )
):
    """
    Protect owner-only backend operations.
    """

    stored_hash = None

    # Import this from the session manager later.
    # For now this is intentionally not hardcoded.
    from backend.security.session import (
        get_owner_token_hash
    )

    stored_hash = get_owner_token_hash()

    if not verify_owner_token(
        x_medha_owner_token,
        stored_hash
    ):
        raise HTTPException(
            status_code=403,
            detail="Owner authorization required."
        )

    return True