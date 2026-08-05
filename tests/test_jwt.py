"""Provides the Test Jwt test module for the backend application."""

from datetime import timedelta

import pytest
from fastapi import HTTPException

from service.auth.JWT.JWT_token import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    verify_token,
)


def _auth_error():
    return HTTPException(status_code=401, detail="invalid token")


def test_access_token_round_trip():
    token = create_access_token(
        {"sub": "user-123"},
        expire_delta=timedelta(minutes=5),
    )

    token_data = verify_token(token, _auth_error())

    assert token_data.user_id == "user-123"


def test_refresh_token_round_trip():
    token = create_refresh_token({"sub": "user-456"})

    token_data = verify_refresh_token(token, _auth_error())

    assert token_data.user_id == "user-456"


def test_invalid_token_raises_http_exception():
    with pytest.raises(HTTPException) as exc:
        verify_token("not.a.valid.jwt", _auth_error())

    assert exc.value.status_code == 401
    assert exc.value.detail == "invalid token"
