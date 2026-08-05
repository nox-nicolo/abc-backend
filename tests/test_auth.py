"""Provides the Test Auth test module for the backend application."""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from core.enumeration import AccountAccessStatus
from models.auth.profile_picture import ProfilePicture
from models.auth.refresh_token import RefreshToken
from models.auth.user import User
from models.auth.verification import Verification
from models.account.audit import UserAuditEvent
from service.auth.password_reset import request_password_reset, reset_password
from service.auth.login_user import login_user

from tests.conftest import make_user


@pytest.fixture()
def auth_db(db_session_factory):
    yield from db_session_factory(
        [
            User.__table__,
            ProfilePicture.__table__,
            RefreshToken.__table__,
            Verification.__table__,
            UserAuditEvent.__table__,
        ]
    )


def _login_payload(username: str, password: str = "Password123!"):
    return SimpleNamespace(username=username, password=password)


def test_login_returns_tokens_and_persists_refresh_token(auth_db):
    user = make_user(username="active_user", email="active@example.test")
    auth_db.add(user)
    auth_db.commit()

    result = login_user(_login_payload("active_user"), auth_db)

    assert result["user_id"] == user.id
    assert result["token_type"] == "bearer"
    assert result["access_token"]
    assert result["refresh_token"]

    stored = auth_db.query(RefreshToken).filter_by(user_id=user.id).one()
    assert stored.token == result["refresh_token"]
    assert stored.revoked is False


def test_login_rejects_unverified_account(auth_db):
    user = make_user(
        username="pending_user",
        email="pending@example.test",
        is_verified=False,
        account_access=AccountAccessStatus.PENDING,
    )
    auth_db.add(user)
    auth_db.commit()

    with pytest.raises(HTTPException) as exc:
        login_user(_login_payload("pending_user"), auth_db)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Account is not verified"


def test_login_rejects_wrong_password(auth_db):
    user = make_user(username="wrong_password")
    auth_db.add(user)
    auth_db.commit()

    with pytest.raises(HTTPException) as exc:
        login_user(_login_payload("wrong_password", password="bad-password"), auth_db)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Incorrect password"


@pytest.mark.anyio
async def test_password_reset_updates_password_and_revokes_sessions(auth_db, monkeypatch):
    sent_links = []

    user = make_user(username="reset_user", email="reset@example.test")
    token = RefreshToken(token="refresh-token", user_id=user.id, revoked=False)
    auth_db.add_all([user, token])
    auth_db.commit()

    async def fake_password_reset_mail_send(reset_link: str, email: str):
        sent_links.append(reset_link)

    monkeypatch.setattr(
        "service.auth.password_reset.password_reset_mail_send",
        fake_password_reset_mail_send,
    )

    result = await request_password_reset("reset@example.test", auth_db)

    assert result["detail"] == "If an account exists, a password reset link has been sent."
    assert sent_links
    reset_token = sent_links[0].split("token=", 1)[1]

    reset = reset_password(
        token=reset_token,
        new_password="NewPassword123!",
        db=auth_db,
    )

    assert reset["detail"] == "Password reset successfully. Please sign in again."
    assert login_user(_login_payload("reset_user", "NewPassword123!"), auth_db)
    assert auth_db.query(RefreshToken).filter_by(token="refresh-token").one().revoked is True


def test_password_reset_rejects_invalid_code(auth_db):
    user = make_user(username="reset_invalid", email="invalid-reset@example.test")
    auth_db.add(user)
    auth_db.commit()

    with pytest.raises(HTTPException) as exc:
        reset_password(
            token="not-a-real-token",
            new_password="NewPassword123!",
            db=auth_db,
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Invalid or expired reset link"
