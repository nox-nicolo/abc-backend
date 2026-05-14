import os
import uuid
from collections.abc import Iterable
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("JWT_SECRET", "test-secret-for-automated-tests")
os.environ.setdefault("BASE_URL", "https://example.test")

import models.registry  # noqa: E402,F401
from core.enumeration import AccountAccessStatus  # noqa: E402
from core.hash_pass import Hash  # noqa: E402
from models.auth.user import User  # noqa: E402
from models.base import Base  # noqa: E402


def _engine():
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture()
def db_session_factory():
    def build(tables: Iterable):
        engine = _engine()
        Base.metadata.create_all(bind=engine, tables=list(tables))
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()
            Base.metadata.drop_all(bind=engine, tables=list(tables))
            engine.dispose()

    return build


def make_user(
    *,
    user_id: str | None = None,
    username: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    password: str = "Password123!",
    role: str = "customer",
    is_verified: bool = True,
    account_access: AccountAccessStatus = AccountAccessStatus.ACTIVE,
) -> User:
    suffix = uuid.uuid4().hex[:8]
    return User(
        id=user_id or str(uuid.uuid4()),
        username=username or f"user_{suffix}",
        name="Test User",
        email=email or f"user_{suffix}@example.test",
        phone=phone or f"+2557{suffix[:7]}",
        password=Hash.hashing(password),
        role=role,
        is_verified=is_verified,
        account_access=account_access,
        created_at=datetime.now(timezone.utc),
    )
