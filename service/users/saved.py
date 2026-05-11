import uuid

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from core.enumeration import ImageURL
from models.auth.profile_picture import ProfilePicture
from models.posts.posts import MediaData, Post, PostBoorkmark
from models.profile.salon import Salon, SalonServicePrice
from models.saved import SavedSalon, SavedService
from models.services.service import Services, SubServices


PROFILE_IMAGE_BASE = ImageURL.PROFILE_URL.value


def toggle_saved_salon(*, user_id: str, salon_id: str, db: Session):
    salon = db.query(Salon).filter(Salon.id == salon_id).first()
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")

    saved = (
        db.query(SavedSalon)
        .filter(SavedSalon.user_id == user_id, SavedSalon.salon_id == salon_id)
        .first()
    )
    if saved:
        db.delete(saved)
        db.commit()
        return {"salon_id": salon_id, "saved": False}

    db.add(SavedSalon(id=str(uuid.uuid4()), user_id=user_id, salon_id=salon_id))
    db.commit()
    return {"salon_id": salon_id, "saved": True}


def toggle_saved_service(*, user_id: str, service_id: str, db: Session):
    target = _resolve_service_target(db, service_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Service not found")

    filters = _saved_service_filters(user_id, target)
    saved = db.query(SavedService).filter(*filters).first()
    if saved:
        db.delete(saved)
        db.commit()
        return {"service_id": service_id, "saved": False}

    db.add(
        SavedService(
            id=str(uuid.uuid4()),
            user_id=user_id,
            service_id=target.get("service_id"),
            sub_service_id=target.get("sub_service_id"),
            salon_service_price_id=target.get("salon_service_price_id"),
        )
    )
    db.commit()
    return {"service_id": service_id, "saved": True}


def toggle_saved_style(*, user_id: str, style_id: str, db: Session):
    post = db.query(Post).filter(Post.id == style_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Style not found")

    saved = (
        db.query(PostBoorkmark)
        .filter(PostBoorkmark.user_id == user_id, PostBoorkmark.post_id == style_id)
        .first()
    )
    if saved:
        db.delete(saved)
        db.commit()
        return {"style_id": style_id, "saved": False}

    db.add(PostBoorkmark(id=str(uuid.uuid4()), user_id=user_id, post_id=style_id))
    db.commit()
    return {"style_id": style_id, "saved": True}


def list_saved_salons(*, user_id: str, db: Session):
    rows = (
        db.query(SavedSalon)
        .options(joinedload(SavedSalon.salon).joinedload(Salon.user))
        .filter(SavedSalon.user_id == user_id)
        .order_by(SavedSalon.created_at.desc())
        .all()
    )

    items = []
    for row in rows:
        salon = row.salon
        owner = salon.user
        profile_picture = (
            db.query(ProfilePicture).filter(ProfilePicture.user_id == owner.id).first()
        )
        items.append(
            {
                "id": salon.id,
                "name": salon.title,
                "username": owner.username,
                "slogan": salon.slogan,
                "profile_picture": (
                    f"{PROFILE_IMAGE_BASE}{profile_picture.file_name}"
                    if profile_picture
                    else None
                ),
                "saved_at": row.created_at,
            }
        )
    return {"items": items}


def list_saved_services(*, user_id: str, db: Session):
    rows = (
        db.query(SavedService)
        .options(
            joinedload(SavedService.service),
            joinedload(SavedService.sub_service).joinedload(SubServices.services),
            joinedload(SavedService.salon_service_price).joinedload(SalonServicePrice.salon),
            joinedload(SavedService.salon_service_price).joinedload(SalonServicePrice.service),
            joinedload(SavedService.salon_service_price).joinedload(SalonServicePrice.sub_service),
        )
        .filter(SavedService.user_id == user_id)
        .order_by(SavedService.created_at.desc())
        .all()
    )

    return {"items": [_serialize_saved_service(row) for row in rows]}


def list_saved_styles(*, user_id: str, db: Session):
    rows = (
        db.query(PostBoorkmark)
        .options(joinedload(PostBoorkmark.post).joinedload(Post.user))
        .filter(PostBoorkmark.user_id == user_id)
        .order_by(PostBoorkmark.created_at.desc())
        .all()
    )

    items = []
    for row in rows:
        post = row.post
        if post is None:
            continue
        media = (
            db.query(MediaData)
            .filter(MediaData.post_id == post.id)
            .order_by(MediaData.created_at.asc())
            .first()
        )
        likes_count = len([like for like in post.likes if like.liked])
        items.append(
            {
                "id": post.id,
                "caption": post.caption_text or "Style",
                "image_url": media.media_url if media else None,
                "author_name": post.user.username if post.user else None,
                "likes": likes_count,
                "saved_at": row.created_at,
            }
        )
    return {"items": items}


def _resolve_service_target(db: Session, service_id: str):
    salon_price = db.query(SalonServicePrice).filter(SalonServicePrice.id == service_id).first()
    if salon_price:
        return {"salon_service_price_id": salon_price.id}

    sub_service = db.query(SubServices).filter(SubServices.id == service_id).first()
    if sub_service:
        return {"sub_service_id": sub_service.id}

    service = db.query(Services).filter(Services.id == service_id).first()
    if service:
        return {"service_id": service.id}

    return None


def _saved_service_filters(user_id: str, target: dict):
    filters = [SavedService.user_id == user_id]
    if target.get("salon_service_price_id"):
        filters.append(SavedService.salon_service_price_id == target["salon_service_price_id"])
    elif target.get("sub_service_id"):
        filters.append(SavedService.sub_service_id == target["sub_service_id"])
    else:
        filters.append(SavedService.service_id == target["service_id"])
    return filters


def _serialize_saved_service(row: SavedService):
    if row.salon_service_price:
        price = row.salon_service_price
        service = price.sub_service or price.service
        return {
            "id": price.id,
            "name": service.name if service else "Service",
            "salon_name": price.salon.title if price.salon else None,
            "price": price.price_min,
            "currency": price.currency,
            "saved_at": row.created_at,
        }

    if row.sub_service:
        return {
            "id": row.sub_service.id,
            "name": row.sub_service.name,
            "salon_name": row.sub_service.services.name if row.sub_service.services else None,
            "image_url": row.sub_service.file_name,
            "saved_at": row.created_at,
        }

    service = row.service
    return {
        "id": service.id if service else "",
        "name": service.name if service else "Service",
        "image_url": service.service_picture if service else None,
        "saved_at": row.created_at,
    }
