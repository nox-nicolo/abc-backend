
# from typing import Dict, List, Optional, Tuple
# from fastapi import HTTPException, status
# from sqlalchemy.orm import Session
# from sqlalchemy import or_

# from core.enumeration import ImageURL
# from models.profile.salon import Salon, SalonServicePrice
# from models.services.service import Services, SubServices
# from pydantic_schemas.profile.salon_config_service import SalonServiceSelectableItem, SalonServiceSelectableList

# image_url_major = f"{ImageURL.SERVICE_URL.value}major/"
# image_url_minor = f"{ImageURL.SERVICE_URL.value}minor/"

# def list_selectable_services(
#     *,
#     db: Session,
#     salon_id: str,
#     q: Optional[str] = None,
#     include_archived: bool = False,
#     limit: int = 100,
#     offset: int = 0,
# ) -> SalonServiceSelectableList:
#     """
#     Returns all services/sub-services, annotated with
#     salon configuration state.
#     """
    
#     salon = db.query(Salon).filter(Salon.user_id == salon_id).first()
    
#     # Get the salon Id from the user

#     if not salon:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Salon not found",
#         )
    
#     # Fetch salon-configured services
#     salon_services = (
#         db.query(SalonServicePrice)
#         .filter(SalonServicePrice.salon_id == salon.id)
#         .all()
#     )
    

#     # Build lookup:
#     # (service_id, sub_service_id) -> SalonServicePrice
#     salon_service_map: Dict[
#         Tuple[str, Optional[str]],
#         SalonServicePrice,
#     ] = {}

#     for ssp in salon_services:
#         key = (ssp.service_id, ssp.sub_service_id)
#         salon_service_map[key] = ssp

#     # Fetch platform services + sub-services
#     services_query = db.query(Services)

#     if q:
#         services_query = services_query.filter(
#             or_(
#                 Services.name.ilike(f"%{q}%"),
#                 Services.sub_services.any(
#                     SubServices.name.ilike(f"%{q}%")
#                 ),
#             )
#         )

#     services = (
#         services_query
#         .order_by(Services.name.asc())
#         .offset(offset)
#         .limit(limit)
#         .all()
#     )

#     items: List[SalonServiceSelectableItem] = []

#     # Merge platform + salon state
#     for service in services:
#         # If service has sub-services, list them
#         if service.sub_services:
#             for sub in service.sub_services:
#                 key = (service.id, sub.id)
#                 ssp = salon_service_map.get(key)

#                 if (
#                     ssp
#                     and not include_archived
#                     and ssp.status.name == "ARCHIVED"
#                 ):
#                     continue

#                 items.append(
#                     SalonServiceSelectableItem(
#                         service_id=service.id,
#                         service_name=service.name,
#                         service_image=image_url_minor + sub.file_name if sub.file_name else None,

#                         sub_service_id=sub.id,
#                         sub_service_name=sub.name,

#                         is_configured=ssp is not None,
#                         salon_service_price_id=ssp.id if ssp else None,
#                         status=ssp.status if ssp else None,
#                     )
#                 )
#         else:
#             # Service without sub-services
#             key = (service.id, None)
#             ssp = salon_service_map.get(key)

#             if (
#                 ssp
#                 and not include_archived
#                 and ssp.status.name == "ARCHIVED"
#             ):
#                 continue

#             items.append(
#                 SalonServiceSelectableItem(
#                     service_id=service.id,
#                     service_name=service.name,
#                     service_image=image_url_major + service.service_picture if service.service_picture else None,

#                     sub_service_id=None,
#                     sub_service_name=None,

#                     is_configured=ssp is not None,
#                     salon_service_price_id=ssp.id if ssp else None,
#                     status=ssp.status if ssp else None,
#                 )
#             )

#     return SalonServiceSelectableList(items=items)


from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from core.r2_config import BASE_URL
from core.enumeration import ImageDirectories
from models.profile.salon import Salon, SalonServicePrice
from models.services.service import Services, SubServices
from pydantic_schemas.profile.salon_config_service import SalonServiceSelectableItem, SalonServiceSelectableList

image_url_major = f"{BASE_URL}/{ImageDirectories.SERVICE_DIR.value}major/"
image_url_minor = f"{BASE_URL}/{ImageDirectories.SERVICE_DIR.value}minor/"


def list_selectable_services(
    *,
    db: Session,
    salon_id: str,
    q: Optional[str] = None,
    include_archived: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> SalonServiceSelectableList:
    """
    Returns all services/sub-services, annotated with
    salon configuration state.
    """

    salon = db.query(Salon).filter(Salon.user_id == salon_id).first()

    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found",
        )

    salon_services = (
        db.query(SalonServicePrice)
        .filter(SalonServicePrice.salon_id == salon.id)
        .all()
    )

    salon_service_map: Dict[
        Tuple[str, Optional[str]],
        SalonServicePrice,
    ] = {}

    for ssp in salon_services:
        key = (ssp.service_id, ssp.sub_service_id)
        salon_service_map[key] = ssp

    services_query = db.query(Services)

    if q:
        services_query = services_query.filter(
            or_(
                Services.name.ilike(f"%{q}%"),
                Services.sub_services.any(
                    SubServices.name.ilike(f"%{q}%")
                ),
            )
        )

    services = (
        services_query
        .order_by(Services.name.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items: List[SalonServiceSelectableItem] = []

    for service in services:
        if service.sub_services:
            for sub in service.sub_services:
                key = (service.id, sub.id)
                ssp = salon_service_map.get(key)

                if (
                    ssp
                    and not include_archived
                    and ssp.status.name == "ARCHIVED"
                ):
                    continue

                items.append(
                    SalonServiceSelectableItem(
                        service_id=service.id,
                        service_name=service.name,
                        service_image=(
                            image_url_minor + sub.file_name
                            if sub.file_name else None
                        ),
                        sub_service_id=sub.id,
                        sub_service_name=sub.name,
                        is_configured=ssp is not None,
                        salon_service_price_id=ssp.id if ssp else None,
                        status=ssp.status if ssp else None,
                    )
                )
        else:
            key = (service.id, None)
            ssp = salon_service_map.get(key)

            if (
                ssp
                and not include_archived
                and ssp.status.name == "ARCHIVED"
            ):
                continue

            items.append(
                SalonServiceSelectableItem(
                    service_id=service.id,
                    service_name=service.name,
                    service_image=(
                        image_url_major + service.service_picture
                        if service.service_picture else None
                    ),
                    sub_service_id=None,
                    sub_service_name=None,
                    is_configured=ssp is not None,
                    salon_service_price_id=ssp.id if ssp else None,
                    status=ssp.status if ssp else None,
                )
            )

    return SalonServiceSelectableList(items=items)