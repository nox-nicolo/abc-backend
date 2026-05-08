from datetime import datetime, timedelta
import uuid
import secrets

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from core.database import get_db
from core.enumeration import AccountAccessStatus, Status
from models.auth.user import User
from models.auth.verification import Verification
from models.profile.salon import Salon
from service.auth.JWT.JWT_token import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    create_refresh_token,
)
from service.auth.send_code import enqueue_verification_email, mail_send


# Generate a random 6-digit numeric code
def code_generate(length: int = 6) -> str:
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def expire_time():
    return datetime.now() + timedelta(days=1)


async def create_verification(user: User, via: str, db: Session = Depends(get_db)):
    """
    Creates a new verification record for a user and sends the code.
    """

    verification_code = code_generate()
    expires_at = expire_time()

    verification = Verification(
        id=str(uuid.uuid4()),
        user_id=user.id,
        code=verification_code,
        via=via,
        expires_at=expires_at,
        status=Status.PENDING,
    )

    db.add(verification)
    db.commit()

    if not enqueue_verification_email(code=verification_code, email=user.email):
        await mail_send(code=verification_code, email=user.email)


def verify_user(code: str, db: Session = Depends(get_db)):
    """
    Verify a user using a verification code.
    """

    verification = (
        db.query(Verification)
        .filter(
            Verification.code == code,
            Verification.expires_at > datetime.now(),
            Verification.status == Status.PENDING,
        )
        .first()
    )

    if not verification:
        existing = (
            db.query(Verification)
            .filter(Verification.code == code)
            .first()
        )

        if existing and existing.status == Status.SUCCESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account is Verified",
            )

        if existing and existing.expires_at < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification code expired, Get new Code",
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

    verification.status = Status.SUCCESS

    user = (
        db.query(User)
        .options(joinedload(User.verification))
        .filter(User.id == verification.user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.is_verified = True
    user.account_access = AccountAccessStatus.ACTIVE

    # Create salon for service users if missing
    if str(user.role).lower() == "service":
        existing_salon = (
            db.query(Salon)
            .filter(Salon.user_id == user.id)
            .first()
        )

        if not existing_salon:
            salon = Salon(
                id=str(uuid.uuid4()),
                user_id=user.id,
                title=f"{user.username}'s Salon" if user.username else "My Salon",
                slogan="Your beauty, our duty",
                description="Welcome to our salon!",
                display_ads="Not Set",
                profile_completion=0.0,
            )
            db.add(salon)

    db.commit()
    db.refresh(user)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id},
        expire_delta=access_token_expires,
    )

    refresh_token = create_refresh_token(
        data={"sub": str(user.id)}
    )

    return {
        "user_id": user.id,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


async def code_expires(code: str, db: Session = Depends(get_db)):
    """
    Regenerate and resend a new verification code if the old one expired.
    """

    valid_code = (
        db.query(Verification)
        .filter(
            Verification.code == code,
            Verification.expires_at < datetime.now(),
            Verification.status == Status.PENDING,
        )
        .first()
    )

    if not valid_code:
        verification = (
            db.query(Verification)
            .filter(Verification.code == code)
            .first()
        )

        if verification and verification.status == Status.SUCCESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account is Verified",
            )

        if verification and verification.expires_at > datetime.now():
            raise HTTPException(
                status_code=status.HTTP_200_OK,
                detail="Go to your mail",
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Input Code is invalid",
        )

    user = db.query(User).filter(User.id == valid_code.user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    new_code = code_generate()
    valid_code.code = new_code
    valid_code.expires_at = expire_time()

    db.commit()

    if not enqueue_verification_email(code=new_code, email=user.email):
        await mail_send(code=new_code, email=user.email)

    return {"message": "New Code sent to your mail"}
