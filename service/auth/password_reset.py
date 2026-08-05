"""Provides the Password Reset business logic module for auth workflows."""

from datetime import datetime, timedelta
import os
import secrets
import uuid
from urllib.parse import urlencode

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.enumeration import Status
from core.hash_pass import Hash
from models.auth.refresh_token import RefreshToken
from models.auth.user import User
from models.auth.verification import Verification
from service.account.audit import record_audit_event
from service.auth.send_code import password_reset_mail_send


RESET_VIA = "password_reset"


def _reset_expires_at():
    return datetime.now() + timedelta(minutes=15)


def _reset_link(token: str) -> str:
    reset_url = os.getenv("PASSWORD_RESET_URL") or f"{os.getenv('BASE_URL', '').rstrip('/')}/reset-password"
    return f"{reset_url}?{urlencode({'token': token})}"


async def request_password_reset(email: str, db: Session):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"detail": "If an account exists, a password reset link has been sent."}

    db.query(Verification).filter(
        Verification.user_id == user.id,
        Verification.via == RESET_VIA,
        Verification.status == Status.PENDING,
    ).update({"status": Status.FAILED}, synchronize_session=False)

    token = secrets.token_urlsafe(32)
    verification = Verification(
        id=str(uuid.uuid4()),
        user_id=user.id,
        via=RESET_VIA,
        code="password_reset",
        token=token,
        expires_at=_reset_expires_at(),
        status=Status.PENDING,
    )
    db.add(verification)
    db.commit()

    await password_reset_mail_send(reset_link=_reset_link(token), email=user.email)

    return {"detail": "If an account exists, a password reset link has been sent."}


def reset_password(token: str, new_password: str, db: Session):
    verification = (
        db.query(Verification)
        .filter(
            Verification.via == RESET_VIA,
            Verification.token == token,
            Verification.expires_at > datetime.now(),
            Verification.status == Status.PENDING,
        )
        .first()
    )

    if not verification:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link",
        )

    user = db.query(User).filter(User.id == verification.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link",
        )

    verification.status = Status.SUCCESS
    user.password = Hash.hashing(new_password)
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked == False,
    ).update({"revoked": True}, synchronize_session=False)
    db.commit()

    record_audit_event(
        db,
        user_id=user.id,
        event_type="password_reset",
        title="Password reset",
        description="Account password was reset and active sessions were revoked.",
        metadata={"sessions_revoked": True},
    )
    return {"detail": "Password reset successfully. Please sign in again."}
