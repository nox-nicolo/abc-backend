from sqlalchemy.orm import Session

from models.account.settings import UserAccountSettings
from pydantic_schemas.account.settings import AccountSettingsUpdate


def _get_or_create(db: Session, user_id: str) -> UserAccountSettings:
    row = (
        db.query(UserAccountSettings)
        .filter(UserAccountSettings.user_id == user_id)
        .first()
    )
    if row is None:
        row = UserAccountSettings(user_id=user_id, settings={})
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def get_account_settings(db: Session, user_id: str) -> dict:
    return {"settings": dict(_get_or_create(db, user_id).settings or {})}


def update_account_settings(
    db: Session,
    user_id: str,
    payload: AccountSettingsUpdate,
) -> dict:
    row = _get_or_create(db, user_id)
    current = dict(row.settings or {})
    for key, value in payload.settings.items():
        if value is None:
            current.pop(key, None)
        else:
            current[key] = value
    row.settings = current
    db.commit()
    db.refresh(row)
    return {"settings": dict(row.settings or {})}
