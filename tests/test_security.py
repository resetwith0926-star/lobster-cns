from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.security import scrub_secret, validate_admin_secret


def test_admin_secret_rejects_missing_header():
    with pytest.raises(HTTPException) as exc_info:
        validate_admin_secret(None, expected_secret="local-secret")

    assert exc_info.value.status_code == 401


def test_admin_secret_rejects_wrong_header():
    with pytest.raises(HTTPException) as exc_info:
        validate_admin_secret("wrong", expected_secret="local-secret")

    assert exc_info.value.status_code == 401


def test_admin_secret_accepts_correct_header():
    assert validate_admin_secret("local-secret", expected_secret="local-secret") is True


def test_scrub_secret_does_not_return_full_secret():
    secret = "sk-test-very-sensitive-key"

    scrubbed = scrub_secret(secret)

    assert secret not in scrubbed
    assert scrubbed.startswith("sk-t")
