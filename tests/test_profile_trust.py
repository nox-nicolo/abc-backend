"""Provides the Test Profile Trust test module for the backend application."""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from models.auth.user import User
from models.auth.verification import Verification
from models.profile.salon import Salon, SalonContact, SalonReport
from models.profile.trust import SalonBusinessDocument
from service.auth.permissions import SalonPrincipal, UserPrincipal
from service.profile.trust import get_trust_status, upload_business_document
from tests.conftest import make_user


@pytest.fixture()
def trust_db(db_session_factory):
    yield from db_session_factory(
        [
            User.__table__,
            Verification.__table__,
            Salon.__table__,
            SalonContact.__table__,
            SalonReport.__table__,
            SalonBusinessDocument.__table__,
        ]
    )


def test_customer_trust_uses_email_and_phone_verification(trust_db):
    user = make_user(user_id="customer-1", role="customer", is_verified=True)
    trust_db.add_all(
        [
            user,
            Verification(
                id="verification-1",
                user_id=user.id,
                via="phone",
                code="123456",
                token="token-1",
                phone_verified=True,
            ),
        ]
    )
    trust_db.commit()

    result = get_trust_status(
        db=trust_db,
        principal=UserPrincipal(user_id=user.id, role="customer", user=user),
    )

    assert result["verified_email"] is True
    assert result["verified_phone"] is True
    assert result["safety_badge"] is True


def test_salon_trust_tracks_document_review_status(trust_db):
    owner = make_user(user_id="owner-1", role="service", is_verified=True)
    salon = Salon(id="salon-1", user_id=owner.id, title="Salon")
    trust_db.add_all(
        [
            owner,
            salon,
            SalonContact(
                id="contact-1",
                salon_id=salon.id,
                type="phone",
                value="+255700000000",
                is_primary=True,
                is_verified=True,
            ),
            SalonBusinessDocument(
                id="document-1",
                salon_id=salon.id,
                uploaded_by_user_id=owner.id,
                document_type="business_license",
                file_name="license.pdf",
                review_status="approved",
                created_at=datetime.now(timezone.utc),
            ),
        ]
    )
    trust_db.commit()

    result = get_trust_status(
        db=trust_db,
        principal=SalonPrincipal(
            user_id=owner.id,
            role="salon_owner",
            user=owner,
            salon_id=salon.id,
            salon=salon,
        ),
    )

    assert result["business_document_uploaded"] is True
    assert result["profile_review_status"] == "approved"
    assert result["verified_salon_owner"] is True
    assert result["safety_badge"] is True


@pytest.mark.anyio
async def test_salon_business_document_upload_creates_pending_review(trust_db, tmp_path, monkeypatch):
    owner = make_user(user_id="owner-1", role="service", is_verified=True)
    salon = Salon(id="salon-1", user_id=owner.id, title="Salon")
    trust_db.add_all([owner, salon])
    trust_db.commit()
    monkeypatch.setattr("service.profile.trust.DOCUMENT_DIR", tmp_path)

    document = SimpleNamespace(
        filename="license.png",
        read=lambda: _async_bytes(b"fake image bytes"),
    )

    result = await upload_business_document(
        db=trust_db,
        salon_owner=SalonPrincipal(
            user_id=owner.id,
            role="salon_owner",
            user=owner,
            salon_id=salon.id,
            salon=salon,
        ),
        document=document,
        document_type="business_license",
    )

    stored = trust_db.query(SalonBusinessDocument).filter_by(id=result["id"]).one()
    assert result["review_status"] == "pending"
    assert stored.document_type == "business_license"


async def _async_bytes(value: bytes) -> bytes:
    return value
