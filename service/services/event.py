from sqlalchemy.orm import Session, joinedload
from sqlalchemy import outerjoin
from models.services.service import SubServices
from models.profile.salon import Salon, SalonServicePrice
from models.auth.user import User


def get_featured_events(db: Session, limit: int = 10, offset: int = 0):
    query = (
        db.query(SubServices, SalonServicePrice, Salon)
        .outerjoin(
            SalonServicePrice,
            SalonServicePrice.sub_service_id == SubServices.id
        )
        .outerjoin(
            Salon,
            Salon.id == SalonServicePrice.salon_id
        )
        .options(
            joinedload(Salon.user).joinedload(User.profile_picture),
        )
        .filter(SubServices.is_event == True)
    )
    total = query.count()
    rows = (
        query
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows, total
