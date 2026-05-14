from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from core.enumeration import AccountAccessStatus
from models.auth.profile_picture import ProfilePicture
from models.auth.refresh_token import RefreshToken
from models.auth.user import User
from service.auth.login_user import login_user

from tests.conftest import make_user


@pytest.fixture()
def auth_db(db_session_factory):
    yield from db_session_factory(
        [
            User.__table__,
            ProfilePicture.__table__,
            RefreshToken.__table__,
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
