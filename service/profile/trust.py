"""Provides the Trust business logic module for profile workflows."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from models.auth.verification import Verification
from models.profile.salon import SalonContact, SalonReport
from models.profile.trust import SalonBusinessDocument
from service.auth.permissions import ROLE_SALON_OWNER, SalonPrincipal, UserPrincipal


DOCUMENT_DIR = Path("assets/business_documents")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}


def get_trust_status(*, db: Session, principal: UserPrincipal) -> dict:
    if principal.role == ROLE_SALON_OWNER:
        return _salon_trust_status(db=db, principal=principal)
    return _customer_trust_status(db=db, principal=principal)


async def upload_business_document(
    *,
    db: Session,
    salon_owner: SalonPrincipal,
    document: UploadFile,
    document_type: str = "business_document",
) -> dict:
    extension = Path(document.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Business document must be a JPG, PNG, or PDF file",
        )

    content = await document.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Business document must be 5MB or smaller",
        )

    DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)
    file_name = f"{salon_owner.salon_id}_{uuid.uuid4().hex}{extension}"
    (DOCUMENT_DIR / file_name).write_bytes(content)

    db.query(SalonBusinessDocument).filter(
        SalonBusinessDocument.salon_id == salon_owner.salon_id,
        SalonBusinessDocument.review_status == "pending",
    ).update({"review_status": "superseded"}, synchronize_session=False)

    record = SalonBusinessDocument(
        salon_id=salon_owner.salon_id,
        uploaded_by_user_id=salon_owner.user_id,
        document_type=document_type,
        file_name=file_name,
        review_status="pending",
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "id": record.id,
        "review_status": record.review_status,
        "detail": "Business document uploaded for review",
    }


def _customer_trust_status(*, db: Session, principal: UserPrincipal) -> dict:
    verified_email = bool(principal.user.is_verified)
    verified_phone = _phone_verified(db=db, user_id=principal.user_id)
    safety_badge = verified_email and verified_phone

    return {
        "role": "customer",
        "verified_email": verified_email,
        "verified_phone": verified_phone,
        "verified_salon_owner": False,
        "business_document_uploaded": False,
        "profile_review_status": "not_applicable",
        "safety_badge": safety_badge,
        "indicators": [
            _indicator("verified_email", "Verified email", verified_email),
            _indicator("verified_phone", "Verified phone", verified_phone),
            _indicator(
                "safety_badge",
                "Safety badge",
                safety_badge,
                met_detail="Email and phone are verified.",
                missing_detail="Verify email and phone to earn this badge.",
            ),
        ],
    }


def _salon_trust_status(*, db: Session, principal: UserPrincipal) -> dict:
    salon = principal.salon
    verified_email = bool(principal.user.is_verified) or _verified_contact(
        db=db,
        salon_id=salon.id,
        contact_type="email",
    )
    verified_phone = _verified_contact(db=db, salon_id=salon.id, contact_type="phone")
    document = (
        db.query(SalonBusinessDocument)
        .filter(SalonBusinessDocument.salon_id == salon.id)
        .order_by(SalonBusinessDocument.created_at.desc())
        .first()
    )
    business_document_uploaded = document is not None
    profile_review_status = document.review_status if document else "not_submitted"
    reports_count = (
        db.query(func.count(SalonReport.id))
        .filter(SalonReport.salon_id == salon.id)
        .scalar()
        or 0
    )
    verified_salon_owner = (
        verified_email
        and verified_phone
        and profile_review_status in {"approved", "verified"}
    )
    safety_badge = verified_salon_owner and reports_count == 0

    return {
        "role": "salon",
        "verified_email": verified_email,
        "verified_phone": verified_phone,
        "verified_salon_owner": verified_salon_owner,
        "business_document_uploaded": business_document_uploaded,
        "profile_review_status": profile_review_status,
        "safety_badge": safety_badge,
        "indicators": [
            _indicator("verified_email", "Verified email", verified_email),
            _indicator("verified_phone", "Verified phone", verified_phone),
            _indicator(
                "business_document_uploaded",
                "Business document uploaded",
                business_document_uploaded,
                met_detail=f"Review status: {profile_review_status}.",
                missing_detail="Upload a business registration or ownership document.",
            ),
            _indicator(
                "verified_salon_owner",
                "Verified salon owner",
                verified_salon_owner,
                met_detail="Owner identity and business document are verified.",
                missing_detail="Complete email, phone, and business document review.",
            ),
            _indicator(
                "safety_badge",
                "Safety badge",
                safety_badge,
                met_detail="Verified owner with a clean safety record.",
                missing_detail="Complete verification and keep a clean safety record.",
            ),
        ],
    }


def _verified_contact(*, db: Session, salon_id: str, contact_type: str) -> bool:
    return (
        db.query(SalonContact.id)
        .filter(
            SalonContact.salon_id == salon_id,
            SalonContact.type == contact_type,
            SalonContact.is_verified == True,
        )
        .first()
        is not None
    )


def _phone_verified(*, db: Session, user_id: str) -> bool:
    verification = db.query(Verification).filter(Verification.user_id == user_id).first()
    return bool(verification and verification.phone_verified)


def _indicator(
    key: str,
    label: str,
    is_met: bool,
    *,
    met_detail: str | None = None,
    missing_detail: str | None = None,
) -> dict:
    return {
        "key": key,
        "label": label,
        "is_met": is_met,
        "status": "verified" if is_met else "missing",
        "detail": met_detail if is_met else (missing_detail or "Not verified yet."),
    }
