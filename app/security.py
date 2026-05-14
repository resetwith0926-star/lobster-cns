from __future__ import annotations

import hmac
from typing import Optional

from fastapi import Header, HTTPException, status

from app.config import settings


def validate_admin_secret(
    provided_secret: Optional[str],
    expected_secret: Optional[str] = None,
) -> bool:
    expected = expected_secret if expected_secret is not None else settings.admin_secret
    if not provided_secret or not hmac.compare_digest(provided_secret, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid admin secret.",
        )
    return True


def require_admin_secret(
    x_admin_secret: Optional[str] = Header(default=None, alias="X-Admin-Secret"),
) -> bool:
    return validate_admin_secret(x_admin_secret)


def scrub_secret(value: str, visible_chars: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= visible_chars:
        return "*" * len(value)
    return f"{value[:visible_chars]}{'*' * 8}"
