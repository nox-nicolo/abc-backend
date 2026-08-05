"""Provides the Configure Service Salon business logic module for profile workflows."""

# # from fastapi import HTTPException
# # from sqlalchemy.orm import Session
# # from typing import List, Dict, Tuple

# # from core.enumeration import ImageURL
# # from models.profile.salon import (
# #     Salon,
# #     SalonServicePrice,
# #     SalonServiceBenefit,
# #     SalonServiceProduct,
# #     StylistService,
# # )
# # from models.services.service import Services, SubServices
# # from pydantic_schemas.profile.config_service_salon import SalonServiceBenefitOut, SalonServiceConfigOut, SalonServiceProductOut, SalonServiceSelectableItem #, SalonServiceSelectableResponse

# # image_url_major = f"{ImageURL.SERVICE_URL.value}major/"
# # image_url_minor = f"{ImageURL.SERVICE_URL.value}minor/"


# # # ----------------------------------------------------------------
# # # Get single service for salon configuration (create + edit)
# # # ----------------------------------------------------------------
# # def get_salon_services_for_config(
# #     *,
# #     db: Session,
# #     salon_user_id: str,
# #     service_id: str,
# #     sub_service_id: str | None,
# # ) -> SalonServiceSelectableItem:
# #     """
# #     Returns ONE service + sub-service
# #     with config if exists (edit) or null (create)
# #     """

# #     # Resolve salon
# #     salon = (
# #         db.query(Salon)
# #         .filter(Salon.user_id == salon_user_id)
# #         .first()
# #     )

# #     if not salon:
# #         raise HTTPException(
# #             status_code=404,
# #             detail="Salon not found",
# #         )

# #     # Fetch service
# #     service = (
# #         db.query(Services)
# #         .filter(Services.id == service_id)
# #         .first()
# #     )

# #     if not service:
# #         raise HTTPException(
# #             status_code=404,
# #             detail="Service not found",
# #         )

# #     # Fetch sub-service (optional)
# #     sub_service = None
# #     if sub_service_id:
# #         sub_service = (
# #             db.query(SubServices)
# #             .filter(
# #                 SubServices.id == sub_service_id,
# #                 SubServices.service_id == service.id,
# #             )
# #             .first()
# #         )

# #         if not sub_service:
# #             raise HTTPException(
# #                 status_code=404,
# #                 detail="Sub-service not found",
# #             )

# #     # Fetch salon config (if exists)
# #     salon_config = (
# #         db.query(SalonServicePrice)
# #         .filter(
# #             SalonServicePrice.salon_id == salon.id,
# #             SalonServicePrice.service_id == service.id,
# #             SalonServicePrice.sub_service_id == (
# #                 sub_service.id if sub_service else None
# #             ),
# #         )
# #         .first()
# #     )

# #     # Build response using SAME helper
# #     return _build_selectable_item(
# #         salon_config=salon_config,
# #         service=service,
# #         sub_service=sub_service,
# #         db=db,
# #     )


# # def _build_selectable_item(
# #     *,
# #     salon_config: SalonServicePrice | None,
# #     service: Services,
# #     sub_service: SubServices | None,
# #     db: Session,
# # ) -> SalonServiceSelectableItem:

# #     if salon_config:
# #         # Fetch related config data
# #         benefits = (
# #             db.query(SalonServiceBenefit)
# #             .filter(SalonServiceBenefit.salon_service_price_id == salon_config.id)
# #             .order_by(SalonServiceBenefit.position)
# #             .all()
# #         )

# #         products = (
# #             db.query(SalonServiceProduct)
# #             .filter(SalonServiceProduct.salon_service_price_id == salon_config.id)
# #             .all()
# #         )

# #         stylist_ids = [
# #             ss.stylist_id
# #             for ss in db.query(StylistService)
# #             .filter(StylistService.salon_service_price_id == salon_config.id)
# #             .all()
# #         ]

# #         config = SalonServiceConfigOut(
# #             salon_service_price_id=salon_config.id,
# #             price_min=salon_config.price_min,
# #             price_max=salon_config.price_max,
# #             currency=salon_config.currency,
# #             duration_minutes=salon_config.duration_minutes,
# #             status=salon_config.status,
# #             stylist_ids=stylist_ids,
# #             benefits=[SalonServiceBenefitOut.from_orm(b) for b in benefits],
# #             products=[SalonServiceProductOut.from_orm(p) for p in products],
# #         )
# #     else:
# #         config = None

# #     return SalonServiceSelectableItem(
# #         service_id=service.id,
# #         service_name=service.name,
# #         service_image=image_url_major + service.service_picture if service.service_picture else None,

# #         sub_service_id=sub_service.id if sub_service else None,
# #         sub_service_name=sub_service.name if sub_service else None,
# #         sub_service_image=image_url_minor + sub_service.file_name if sub_service and sub_service.file_name else None,
# #         is_configured=salon_config is not None,
# #         config=config,
# #     )


# from fastapi import HTTPException
# from sqlalchemy.orm import Session

# from core.enumeration import ImageURL
# from models.profile.salon import (
#     Salon,
#     SalonServicePrice,
#     SalonServiceBenefit,
#     SalonServiceProduct,
#     SalonStylist,
#     StylistService,
# )
# from models.services.service import Services, SubServices
# from pydantic_schemas.profile.config_service_salon import (
#     SalonServiceBenefitOut,
#     SalonServiceConfigDetailResponse,
#     SalonServiceConfigOut,
#     SalonServiceConfigStylistOut,
#     SalonServiceProductOut,
#     SalonServiceSelectableItem,
# )

# image_url_major = f"{ImageURL.SERVICE_URL.value}major/"
# image_url_minor = f"{ImageURL.SERVICE_URL.value}minor/"


# # ----------------------------------------------------------------
# # Get single service for salon configuration (create + edit)
# # ----------------------------------------------------------------
# def get_salon_services_for_config(
#     *,
#     db: Session,
#     salon_user_id: str,
#     service_id: str,
#     sub_service_id: str | None,
# ) -> SalonServiceConfigDetailResponse:
#     """
#     Returns ONE service + sub-service
#     with config if exists (edit) or null (create)
#     """

#     salon = (
#         db.query(Salon)
#         .filter(Salon.user_id == salon_user_id)
#         .first()
#     )

#     if not salon:
#         raise HTTPException(
#             status_code=404,
#             detail="Salon not found",
#         )

#     service = (
#         db.query(Services)
#         .filter(Services.id == service_id)
#         .first()
#     )

#     if not service:
#         raise HTTPException(
#             status_code=404,
#             detail="Service not found",
#         )

#     sub_service = None
#     if sub_service_id:
#         sub_service = (
#             db.query(SubServices)
#             .filter(
#                 SubServices.id == sub_service_id,
#                 SubServices.service_id == service.id,
#             )
#             .first()
#         )

#         if not sub_service:
#             raise HTTPException(
#                 status_code=404,
#                 detail="Sub-service not found",
#             )

#     salon_config = (
#         db.query(SalonServicePrice)
#         .filter(
#             SalonServicePrice.salon_id == salon.id,
#             SalonServicePrice.service_id == service.id,
#             SalonServicePrice.sub_service_id == (
#                 sub_service.id if sub_service else None
#             ),
#         )
#         .first()
#     )

#     item = _build_selectable_item(
#         salon_config=salon_config,
#         service=service,
#         sub_service=sub_service,
#         db=db,
#     )

#     return SalonServiceConfigDetailResponse(item=item)


# def _build_selectable_item(
#     *,
#     salon_config: SalonServicePrice | None,
#     service: Services,
#     sub_service: SubServices | None,
#     db: Session,
# ) -> SalonServiceSelectableItem:

#     if salon_config:
#         benefits = (
#             db.query(SalonServiceBenefit)
#             .filter(SalonServiceBenefit.salon_service_price_id == salon_config.id)
#             .order_by(SalonServiceBenefit.position)
#             .all()
#         )

#         products = (
#             db.query(SalonServiceProduct)
#             .filter(SalonServiceProduct.salon_service_price_id == salon_config.id)
#             .all()
#         )

#         stylist_links = (
#             db.query(StylistService)
#             .filter(StylistService.salon_service_price_id == salon_config.id)
#             .all()
#         )

#         stylist_ids = [link.stylist_id for link in stylist_links]

#         stylists = []
#         if stylist_ids:
#             stylist_rows = (
#                 db.query(SalonStylist)
#                 .filter(SalonStylist.id.in_(stylist_ids))
#                 .all()
#             )

#             stylists = [
#                 SalonServiceConfigStylistOut(
#                     id=stylist.id,
#                     name=stylist.title,
#                     image=stylist.user.profile_picture.file_name    ,
#                 )
#                 for stylist in stylist_rows
#             ]

#         config = SalonServiceConfigOut(
#             salon_service_price_id=salon_config.id,
#             price_min=salon_config.price_min,
#             price_max=salon_config.price_max,
#             currency=salon_config.currency,
#             duration_minutes=salon_config.duration_minutes,
#             status=salon_config.status,
#             stylists=stylists,
#             benefits=[SalonServiceBenefitOut.from_orm(b) for b in benefits],
#             products=[SalonServiceProductOut.from_orm(p) for p in products],
#         )
#     else:
#         config = None

#     return SalonServiceSelectableItem(
#         service_id=service.id,
#         service_name=service.name,
#         service_image=image_url_major + service.service_picture
#         if service.service_picture else None,
#         sub_service_id=sub_service.id if sub_service else None,
#         sub_service_name=sub_service.name if sub_service else None,
#         sub_service_image=image_url_minor + sub_service.file_name
#         if sub_service and sub_service.file_name else None,
#         is_configured=salon_config is not None,
#         config=config,
#     )


from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.r2_config import BASE_URL
from core.enumeration import ImageDirectories
from models.profile.salon import (
    Salon,
    SalonServicePrice,
    SalonServiceBenefit,
    SalonServiceProduct,
    SalonStylist,
    StylistService,
)
from models.services.service import Services, SubServices
from pydantic_schemas.profile.config_service_salon import (
    SalonServiceBenefitOut,
    SalonServiceConfigDetailResponse,
    SalonServiceConfigOut,
    SalonServiceConfigStylistOut,
    SalonServiceProductOut,
    SalonServiceSelectableItem,
)

image_url_major = f"{BASE_URL}/{ImageDirectories.SERVICE_DIR.value}major/"
image_url_minor = f"{BASE_URL}/{ImageDirectories.SERVICE_DIR.value}minor/"
profile_url = f"{BASE_URL}/{ImageDirectories.PROFILE_DIR.value}"


def get_salon_services_for_config(
    *,
    db: Session,
    salon_user_id: str,
    service_id: str,
    sub_service_id: str | None,
) -> SalonServiceConfigDetailResponse:
    """
    Returns ONE service + sub-service
    with config if exists (edit) or null (create)
    """

    salon = (
        db.query(Salon)
        .filter(Salon.user_id == salon_user_id)
        .first()
    )

    if not salon:
        raise HTTPException(
            status_code=404,
            detail="Salon not found",
        )

    service = (
        db.query(Services)
        .filter(Services.id == service_id)
        .first()
    )

    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found",
        )

    sub_service = None
    if sub_service_id:
        sub_service = (
            db.query(SubServices)
            .filter(
                SubServices.id == sub_service_id,
                SubServices.service_id == service.id,
            )
            .first()
        )

        if not sub_service:
            raise HTTPException(
                status_code=404,
                detail="Sub-service not found",
            )

    salon_config = (
        db.query(SalonServicePrice)
        .filter(
            SalonServicePrice.salon_id == salon.id,
            SalonServicePrice.service_id == service.id,
            SalonServicePrice.sub_service_id == (
                sub_service.id if sub_service else None
            ),
        )
        .first()
    )

    item = _build_selectable_item(
        salon_config=salon_config,
        service=service,
        sub_service=sub_service,
        db=db,
    )

    return SalonServiceConfigDetailResponse(item=item)


def _build_selectable_item(
    *,
    salon_config: SalonServicePrice | None,
    service: Services,
    sub_service: SubServices | None,
    db: Session,
) -> SalonServiceSelectableItem:

    if salon_config:
        benefits = (
            db.query(SalonServiceBenefit)
            .filter(SalonServiceBenefit.salon_service_price_id == salon_config.id)
            .order_by(SalonServiceBenefit.position)
            .all()
        )

        products = (
            db.query(SalonServiceProduct)
            .filter(SalonServiceProduct.salon_service_price_id == salon_config.id)
            .all()
        )

        stylist_links = (
            db.query(StylistService)
            .filter(StylistService.salon_service_price_id == salon_config.id)
            .all()
        )

        stylist_ids = [link.stylist_id for link in stylist_links]

        stylists = []
        if stylist_ids:
            stylist_rows = (
                db.query(SalonStylist)
                .filter(SalonStylist.id.in_(stylist_ids))
                .all()
            )

            stylists = [
                SalonServiceConfigStylistOut(
                    id=stylist.id,
                    name=stylist.title,
                    image=(
                        f"{profile_url}{stylist.user.profile_picture.file_name}"
                        if stylist.user
                        and stylist.user.profile_picture
                        and stylist.user.profile_picture.file_name
                        else None
                    ),
                )
                for stylist in stylist_rows
            ]

        config = SalonServiceConfigOut(
            salon_service_price_id=salon_config.id,
            price_min=salon_config.price_min,
            price_max=salon_config.price_max,
            currency=salon_config.currency,
            duration_minutes=salon_config.duration_minutes,
            status=salon_config.status,
            stylists=stylists,
            benefits=[SalonServiceBenefitOut.from_orm(b) for b in benefits],
            products=[SalonServiceProductOut.from_orm(p) for p in products],
        )
    else:
        config = None

    return SalonServiceSelectableItem(
        service_id=service.id,
        service_name=service.name,
        service_image=(
            image_url_major + service.service_picture
            if service.service_picture else None
        ),
        sub_service_id=sub_service.id if sub_service else None,
        sub_service_name=sub_service.name if sub_service else None,
        sub_service_image=(
            image_url_minor + sub_service.file_name
            if sub_service and sub_service.file_name else None
        ),
        is_configured=salon_config is not None,
        config=config,
    )