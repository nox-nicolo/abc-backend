from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.auth.user import User
from models.mute import UserMute
from models.posts.posts import Post
from models.profile.salon import Salon

VALID_TARGET_TYPES = {"salon", "user", "post"}


def list_mutes(*, db: Session, user_id: str, target_type: str | None = None) -> dict:
    query = db.query(UserMute).filter(UserMute.user_id == user_id)
    if target_type:
        _validate_target_type(target_type)
        query = query.filter(UserMute.target_type == target_type)
    return {"items": query.order_by(UserMute.created_at.desc()).all()}


def mute_target(*, db: Session, user_id: str, target_type: str, target_id: str) -> UserMute:
    _validate_target(db=db, current_user_id=user_id, target_type=target_type, target_id=target_id)
    existing = (
        db.query(UserMute)
        .filter(
            UserMute.user_id == user_id,
            UserMute.target_type == target_type,
            UserMute.target_id == target_id,
        )
        .first()
    )
    if existing:
        return existing

    row = UserMute(user_id=user_id, target_type=target_type, target_id=target_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def unmute_target(*, db: Session, user_id: str, target_type: str, target_id: str) -> dict:
    _validate_target_type(target_type)
    deleted = (
        db.query(UserMute)
        .filter(
            UserMute.user_id == user_id,
            UserMute.target_type == target_type,
            UserMute.target_id == target_id,
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    return {"muted": False, "deleted": deleted}


def muted_target_ids(*, db: Session, user_id: str, target_type: str) -> set[str]:
    _validate_target_type(target_type)
    rows = (
        db.query(UserMute.target_id)
        .filter(UserMute.user_id == user_id, UserMute.target_type == target_type)
        .all()
    )
    return {row.target_id for row in rows}


def _validate_target_type(target_type: str) -> None:
    if target_type not in VALID_TARGET_TYPES:
        raise HTTPException(status_code=400, detail="Invalid mute target type")


def _validate_target(*, db: Session, current_user_id: str, target_type: str, target_id: str) -> None:
    _validate_target_type(target_type)
    if target_type == "user":
        if target_id == current_user_id:
            raise HTTPException(status_code=400, detail="You cannot mute yourself")
        exists = db.query(User.id).filter(User.id == target_id).first()
    elif target_type == "salon":
        exists = db.query(Salon.id).filter(Salon.id == target_id).first()
    else:
        exists = db.query(Post.id).filter(Post.id == target_id).first()

    if not exists:
        raise HTTPException(status_code=404, detail="Mute target not found")
