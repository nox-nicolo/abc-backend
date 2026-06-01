# from fastapi import HTTPException, status
# from sqlalchemy import func
# from sqlalchemy.orm import Session

# from core.enumeration import ImageURL
# from models.profile.salon import Salon, SalonLocation, SalonServicePrice
# from models.services.service import Services, SubServices
# from pydantic_schemas.services.service_details import ServiceDetailsResponse


# minor_image_url = ImageURL.SERVICE_URL.value + "minor/"
# major_image_url = ImageURL.SERVICE_URL.value + "major/"
# salon_cover_image_url = ImageURL.SALON_COVER_URL.value


# def _build_image_url(base_url: str, image_name: str | None) -> str | None:
#     if not image_name:
#         return None
#     return f"{base_url.rstrip('/')}/{str(image_name).lstrip('/')}"


# def _serialize_major_service(major: Services) -> dict:
#     return {
#         "id": str(major.id),
#         "name": major.name,
#         "image": _build_image_url(major_image_url, major.service_picture),
#         "rating": getattr(major, "rating", None),
#     }


# def _serialize_minor_service(minor: SubServices) -> dict:
#     return {
#         "id": str(minor.id),
#         "service_id": str(minor.service_id),
#         "name": minor.name,
#         "image": _build_image_url(minor_image_url, minor.file_name),
#         "rating": getattr(minor, "rating", None),
#         "is_event": getattr(minor, "is_event", False),
#     }


# async def _get_service_details(
#     *,
#     db: Session,
#     user_id: str,
#     service_id: str,
# ) -> ServiceDetailsResponse:
#     major_service = (
#         db.query(Services)
#         .filter(Services.id == service_id)
#         .first()
#     )

#     if major_service:
#         minor_services = (
#             db.query(SubServices)
#             .filter(SubServices.service_id == major_service.id)
#             .order_by(SubServices.id.asc())
#             .all()
#         )

#         if not minor_services:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="No minor services found under this major service.",
#             )

#         minor_ids = [minor.id for minor in minor_services]

#         query_columns = [
#             Salon.id.label("salon_id"),
#             Salon.title.label("salon_name"),
#             Salon.display_ads.label("salon_image"),
#             SalonLocation.city.label("salon_city"),
#             func.min(SalonServicePrice.price_min).label("price_min"),
#             func.max(SalonServicePrice.price_max).label("price_max"),
#             SalonServicePrice.currency.label("currency"),
#             func.min(SalonServicePrice.duration_minutes).label("duration_minutes"),
#         ]

#         group_by_columns = [
#             Salon.id,
#             Salon.title,
#             Salon.display_ads,
#             SalonLocation.city,
#             SalonServicePrice.currency,
#         ]

#         if hasattr(Salon, "average_rating"):
#             query_columns.append(Salon.average_rating.label("rating"))
#             group_by_columns.append(Salon.average_rating)

#         salon_rows = (
#             db.query(*query_columns)
#             .join(SalonServicePrice, Salon.id == SalonServicePrice.salon_id)
#             .outerjoin(SalonLocation, SalonLocation.salon_id == Salon.id)
#             .filter(SalonServicePrice.sub_service_id.in_(minor_ids))
#             .group_by(*group_by_columns)
#             .all()
#         )

#         return ServiceDetailsResponse(
#             major_service=_serialize_major_service(major_service),
#             minor_service=None,
#             minor_services=[_serialize_minor_service(minor) for minor in minor_services],
#             salon_details=[
#                 {
#                     "salon_id": str(row.salon_id),
#                     "salon_name": row.salon_name,
#                     "salon_image": _build_image_url(
#                         salon_cover_image_url,
#                         row.salon_image,
#                     ),
#                     "salon_city": row.salon_city,
#                     "price_min": row.price_min,
#                     "price_max": row.price_max,
#                     "currency": row.currency,
#                     "duration_minutes": row.duration_minutes,
#                     "rating": getattr(row, "rating", None),
#                 }
#                 for row in salon_rows
#             ],
#         )

#     minor_service = (
#         db.query(SubServices)
#         .filter(SubServices.id == service_id)
#         .first()
#     )

#     if not minor_service:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Service not found.",
#         )

#     major_service = (
#         db.query(Services)
#         .filter(Services.id == minor_service.service_id)
#         .first()
#     )

#     if not major_service:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Parent major service not found.",
#         )

#     query_columns = [
#         Salon.id.label("salon_id"),
#         Salon.title.label("salon_name"),
#         Salon.display_ads.label("salon_image"),
#         SalonLocation.city.label("salon_city"),
#         SalonServicePrice.price_min.label("price_min"),
#         SalonServicePrice.price_max.label("price_max"),
#         SalonServicePrice.currency.label("currency"),
#         SalonServicePrice.duration_minutes.label("duration_minutes"),
#     ]

#     if hasattr(Salon, "average_rating"):
#         query_columns.append(Salon.average_rating.label("rating"))

#     salon_rows = (
#         db.query(*query_columns)
#         .join(SalonServicePrice, Salon.id == SalonServicePrice.salon_id)
#         .outerjoin(SalonLocation, SalonLocation.salon_id == Salon.id)
#         .filter(SalonServicePrice.sub_service_id == minor_service.id)
#         .all()
#     )

#     return ServiceDetailsResponse(
#         major_service=_serialize_major_service(major_service),
#         minor_service=_serialize_minor_service(minor_service),
#         minor_services=None,
#         salon_details=[
#             {
#                 "salon_id": str(row.salon_id),
#                 "salon_name": row.salon_name,
#                 "salon_image": _build_image_url(
#                     salon_cover_image_url,
#                     row.salon_image,
#                 ),
#                 "salon_city": row.salon_city,
#                 "price_min": row.price_min,
#                 "price_max": row.price_max,
#                 "currency": row.currency,
#                 "duration_minutes": row.duration_minutes,
#                 "rating": getattr(row, "rating", None),
#             }
#             for row in salon_rows
#         ],
#     )

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.r2_config import BASE_URL
from core.enumeration import ImageDirectories, ServiceCreatedStatus
from models.profile.salon import Salon, SalonLocation, SalonServicePrice
from models.services.service import Services, SubServices
from pydantic_schemas.services.service_details import ServiceDetailsResponse
from service.booking.ratings import service_rating_summary, sub_service_rating_summary


minor_image_url = f"{BASE_URL}/{ImageDirectories.SERVICE_DIR.value}minor/"
major_image_url = f"{BASE_URL}/{ImageDirectories.SERVICE_DIR.value}major/"
salon_cover_image_url = f"{BASE_URL}/{ImageDirectories.SALON_COVER_DIR.value}"


def _build_image_url(base_url: str, image_name: str | None) -> str | None:
    if not image_name:
        return None
    return f"{base_url.rstrip('/')}/{str(image_name).lstrip('/')}"


def _rating_or_none(summary: dict) -> float | None:
    return summary["average"] if summary["count"] > 0 else None


def _serialize_major_service(
    major: Services,
    *,
    rating: float | None = None,
) -> dict:
    return {
        "id": str(major.id),
        "name": major.name,
        "image": _build_image_url(major_image_url, major.service_picture),
        "rating": rating,
    }


def _serialize_minor_service(
    minor: SubServices,
    *,
    rating: float | None = None,
) -> dict:
    return {
        "id": str(minor.id),
        "service_id": str(minor.service_id),
        "name": minor.name,
        "image": _build_image_url(minor_image_url, minor.file_name),
        "rating": rating,
        "is_event": getattr(minor, "is_event", False),
    }


async def _get_service_details(
    *,
    db: Session,
    user_id: str,
    service_id: str,
) -> ServiceDetailsResponse:
    major_service = (
        db.query(Services)
        .filter(Services.id == service_id)
        .first()
    )

    if major_service:
        minor_services = (
            db.query(SubServices)
            .filter(SubServices.service_id == major_service.id)
            .order_by(SubServices.id.asc())
            .all()
        )

        if not minor_services:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No minor services found under this major service.",
            )

        minor_ids = [minor.id for minor in minor_services]

        query_columns = [
            Salon.id.label("salon_id"),
            Salon.title.label("salon_name"),
            Salon.display_ads.label("salon_image"),
            SalonLocation.city.label("salon_city"),
            func.min(SalonServicePrice.price_min).label("price_min"),
            func.max(SalonServicePrice.price_max).label("price_max"),
            SalonServicePrice.currency.label("currency"),
            func.min(SalonServicePrice.duration_minutes).label("duration_minutes"),
        ]

        group_by_columns = [
            Salon.id,
            Salon.title,
            Salon.display_ads,
            SalonLocation.city,
            SalonServicePrice.currency,
        ]

        salon_rows = (
            db.query(*query_columns)
            .join(SalonServicePrice, Salon.id == SalonServicePrice.salon_id)
            .outerjoin(SalonLocation, SalonLocation.salon_id == Salon.id)
            .filter(
                SalonServicePrice.sub_service_id.in_(minor_ids),
                SalonServicePrice.status == ServiceCreatedStatus.ACTIVE,
                SalonServicePrice.price_min.isnot(None),
                SalonServicePrice.price_min >= 0,
                SalonServicePrice.duration_minutes.isnot(None),
                SalonServicePrice.duration_minutes > 0,
                SalonServicePrice.concurrent_capacity >= 1,
            )
            .group_by(*group_by_columns)
            .all()
        )

        return ServiceDetailsResponse(
            major_service=_serialize_major_service(
                major_service,
                rating=_rating_or_none(
                    service_rating_summary(db, service_id=major_service.id)
                ),
            ),
            minor_service=None,
            minor_services=[
                _serialize_minor_service(
                    minor,
                    rating=_rating_or_none(
                        sub_service_rating_summary(db, sub_service_id=minor.id)
                    ),
                )
                for minor in minor_services
            ],
            salon_details=[
                {
                    "salon_id": str(row.salon_id),
                    "salon_name": row.salon_name,
                    "salon_image": _build_image_url(
                        salon_cover_image_url,
                        row.salon_image,
                    ),
                    "salon_city": row.salon_city,
                    "price_min": row.price_min,
                    "price_max": row.price_max,
                    "currency": row.currency,
                    "duration_minutes": row.duration_minutes,
                    "rating": _rating_or_none(
                        service_rating_summary(
                            db,
                            service_id=major_service.id,
                            salon_id=row.salon_id,
                        )
                    ),
                }
                for row in salon_rows
            ],
        )

    minor_service = (
        db.query(SubServices)
        .filter(SubServices.id == service_id)
        .first()
    )

    if not minor_service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found.",
        )

    major_service = (
        db.query(Services)
        .filter(Services.id == minor_service.service_id)
        .first()
    )

    if not major_service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent major service not found.",
        )

    query_columns = [
        Salon.id.label("salon_id"),
        Salon.title.label("salon_name"),
        Salon.display_ads.label("salon_image"),
        SalonLocation.city.label("salon_city"),
        SalonServicePrice.id.label("salon_service_price_id"),
        SalonServicePrice.price_min.label("price_min"),
        SalonServicePrice.price_max.label("price_max"),
        SalonServicePrice.currency.label("currency"),
        SalonServicePrice.duration_minutes.label("duration_minutes"),
    ]

    salon_rows = (
        db.query(*query_columns)
        .join(SalonServicePrice, Salon.id == SalonServicePrice.salon_id)
        .outerjoin(SalonLocation, SalonLocation.salon_id == Salon.id)
        .filter(
            SalonServicePrice.sub_service_id == minor_service.id,
            SalonServicePrice.status == ServiceCreatedStatus.ACTIVE,
            SalonServicePrice.price_min.isnot(None),
            SalonServicePrice.price_min >= 0,
            SalonServicePrice.duration_minutes.isnot(None),
            SalonServicePrice.duration_minutes > 0,
            SalonServicePrice.concurrent_capacity >= 1,
        )
        .all()
    )

    return ServiceDetailsResponse(
        major_service=_serialize_major_service(
            major_service,
            rating=_rating_or_none(
                service_rating_summary(db, service_id=major_service.id)
            ),
        ),
        minor_service=_serialize_minor_service(
            minor_service,
            rating=_rating_or_none(
                sub_service_rating_summary(db, sub_service_id=minor_service.id)
            ),
        ),
        minor_services=None,
        salon_details=[
            {
                "salon_id": str(row.salon_id),
                "salon_name": row.salon_name,
                "salon_image": _build_image_url(
                    salon_cover_image_url,
                    row.salon_image,
                ),
                "salon_city": row.salon_city,
                "salon_service_price_id": str(row.salon_service_price_id),
                "price_min": row.price_min,
                "price_max": row.price_max,
                "currency": row.currency,
                "duration_minutes": row.duration_minutes,
                "rating": _rating_or_none(
                    sub_service_rating_summary(
                        db,
                        sub_service_id=minor_service.id,
                        salon_id=row.salon_id,
                    )
                ),
            }
            for row in salon_rows
        ],
    )
