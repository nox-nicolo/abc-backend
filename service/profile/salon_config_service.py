import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from models.profile.salon import Salon, SalonServiceBenefit, SalonServicePrice, SalonServiceProduct, SalonStylist, StylistService
from models.services.service import Services, SubServices
from pydantic_schemas.profile.salon_config_service import SalonServiceConfigIn, SalonServiceConfigOut



# ----------------------------------------------------------------
# Create salon service configuration (first-time setup)
# ----------------------------------------------------------------
def create_salon_service(
    *,
    db: Session,
    salon: str,
    payload: SalonServiceConfigIn,
) -> SalonServiceConfigOut:
    """
    Create a salon service configuration (first-time setup).
    """
    # never do this it couples service logic to authit duplicates router responsibility it makes testing harder
    salon_id = salon
    salon = db.query(Salon).filter(Salon.user_id == salon_id).first()
    
    # Get the salon Id from the user

    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found",
        )
        
    # Validate service / sub-service
    if not payload.service_id and not payload.sub_service_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="service_id or sub_service_id is required",
        )

    
    service = None
    sub_service = None

    if payload.service_id:
        service = (
            db.query(Services)
            .filter(Services.id == payload.service_id)
            .first()
        )
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found",
            )

    if payload.sub_service_id:
        sub_service = (
            db.query(SubServices)
            .filter(SubServices.id == payload.sub_service_id)
            .first()
        )
        if not sub_service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sub-service not found",
            )

    # Ensure service is NOT already configured
    existing = (
        db.query(SalonServicePrice)
        .filter(
            SalonServicePrice.salon_id == salon.id,
            SalonServicePrice.service_id == payload.service_id,
            SalonServicePrice.sub_service_id == payload.sub_service_id,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Service already configured for this salon",
        )

    # Create SalonServicePrice
    salon_service = SalonServicePrice(
        id=str(uuid.uuid4()),
        salon_id=salon.id,
        service_id=payload.service_id,
        sub_service_id=payload.sub_service_id,
        price_min=payload.price_min,
        price_max=payload.price_max,
        currency=payload.currency,
        duration_minutes=payload.duration_minutes,
        status=payload.status,
    )

    db.add(salon_service)
    db.flush()  # get salon_service.id

    # Add benefits
    for benefit in payload.benefits:
        db.add(
            SalonServiceBenefit(
                salon_service_price_id=salon_service.id,
                benefit=benefit.benefit,
                position=benefit.position,
            )
        )

    # Add products
    for product in payload.products:
        db.add(
            SalonServiceProduct(
                salon_service_price_id=salon_service.id,
                product_name=product.product_name,
                brand=product.brand,
            )
        )

    # Assign stylists
    unique_ids = set(payload.stylist_ids)

    if payload.stylist_ids:
        stylists = (
        db.query(SalonStylist)
        .filter(
            SalonStylist.id.in_(unique_ids),
            SalonStylist.salon_id == salon.id,
        )
        .all()
    )

        if len(stylists) != len(payload.stylist_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more stylists are invalid for this salon",
            )

        for stylist in stylists:
            db.add(
                StylistService(
                    stylist_id=stylist.id,
                    salon_service_price_id=salon_service.id,
                )
            )

    # Commit transaction
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create salon service",
        )

    db.refresh(salon_service)

    # Return config (edit mode payload)
    return SalonServiceConfigOut(
        id=salon_service.id,
        service_id=salon_service.service_id,
        sub_service_id=salon_service.sub_service_id,
        price_min=salon_service.price_min,
        price_max=salon_service.price_max,
        currency=salon_service.currency,
        duration_minutes=salon_service.duration_minutes,
        status=salon_service.status,
        created_at=salon_service.created_at,
        stylist_ids=payload.stylist_ids,
        benefits=payload.benefits,
        products=payload.products,
    )
    
# ------------------------------------------------------------------


# ----------------------------------------------------------------
# Update salon service configuration (edit mode)
# ----------------------------------------------------------------
def update_salon_service(
    *,
    db: Session,
    salon: str,
    salon_service_price_id: str,
    payload: SalonServiceConfigIn,
) -> SalonServiceConfigOut:
    
    salon_id = salon
    salon = db.query(Salon).filter(Salon.user_id == salon_id).first()

    salon_service = (
        db.query(SalonServicePrice)
        .filter(
            SalonServicePrice.id == salon_service_price_id,
            SalonServicePrice.salon_id == salon.id,
        )
        .first()
    )

    if not salon_service:
        raise HTTPException(status_code=404, detail="Salon service not found")

    salon_service.price_min = payload.price_min
    salon_service.price_max = payload.price_max
    salon_service.currency = payload.currency
    salon_service.duration_minutes = payload.duration_minutes
    salon_service.status = payload.status

    db.query(SalonServiceBenefit).filter(
        SalonServiceBenefit.salon_service_price_id == salon_service.id
    ).delete()

    for benefit in payload.benefits:
        db.add(SalonServiceBenefit(
            salon_service_price_id=salon_service.id,
            benefit=benefit.benefit,
            position=benefit.position,
        ))

    db.query(SalonServiceProduct).filter(
        SalonServiceProduct.salon_service_price_id == salon_service.id
    ).delete()

    for product in payload.products:
        db.add(SalonServiceProduct(
            salon_service_price_id=salon_service.id,
            product_name=product.product_name,
            brand=product.brand,
        ))

    db.query(StylistService).filter(
        StylistService.salon_service_price_id == salon_service.id
    ).delete()

    if payload.stylist_ids:
        unique_ids = set(payload.stylist_ids)

        stylists = (
            db.query(SalonStylist)
            .filter(
                SalonStylist.id.in_(unique_ids),
                SalonStylist.salon_id == salon.id,
            )
            .all()
        )

        if len(stylists) != len(unique_ids):
            raise HTTPException(
                status_code=400,
                detail="One or more stylists are invalid for this salon",
            )

        for stylist in stylists:
            db.add(StylistService(
                stylist_id=stylist.id,
                salon_service_price_id=salon_service.id,
            ))

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Failed to update salon service",
        )

    db.refresh(salon_service)

    return SalonServiceConfigOut(
        id=salon_service.id,
        service_id=salon_service.service_id,
        sub_service_id=salon_service.sub_service_id,
        price_min=salon_service.price_min,
        price_max=salon_service.price_max,
        currency=salon_service.currency,
        duration_minutes=salon_service.duration_minutes,
        status=salon_service.status,
        created_at=salon_service.created_at,
        stylist_ids=list(unique_ids) if payload.stylist_ids else [],
        benefits=payload.benefits,
        products=payload.products,
    )

# ----------------------------------------------------------------