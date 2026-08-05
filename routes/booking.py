"""Provides the Booking API route module for the backend application."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import List, Optional

from core.database import get_db
from core.enumeration import BookingStatus
from core.rate_limit import enforce_rate_limit

from pydantic_schemas.auth.jwt_token import TokenData
from pydantic_schemas.booking.booking import (
    BookingCreate,
    BookingEventResponse,
    BookingResponse,
    BookingAssignStylist,
    BookingCancel,
    AvailabilityResponse,
    BookingListItem,
    BookingListPage,
    BookingResponsePage,
    BookingReschedule,
    BookingReviewCreate,
    BookingReviewResponse,
)

from pydantic_schemas.booking.choose_salon import BookingStylistOptionListResponse, SalonOfferListResponse
from service.auth.JWT.oauth2 import get_current_user
from service.booking.booking import assign_booking_stylist_service, cancel_booking_service, complete_booking_service, confirm_booking_service, create_booking_service, create_review_service, get_availability_slots_service, get_booking_events_service, get_booking_service, get_booking_stylists_for_offer, get_salon_bookings_service, get_salons_for_style, get_user_bookings_service, mark_no_show_service, reject_booking_service, reschedule_booking_service


booking = APIRouter(
    prefix="/booking",
    tags=["Booking"]
)

# -------------------------------------------------------------------
# Create booking
# -------------------------------------------------------------------
@booking.post(
    "",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_booking(
    payload: BookingCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    enforce_rate_limit(
        request,
        bucket="booking:create",
        limit=10,
        window_seconds=300,
        user_id=current_user.user_id,
    )
    try:
        return await create_booking_service(
            db=db,
            payload=payload,
            user_id=current_user.user_id,
        )
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail}
        ) 
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"An unexpected error occurred: {e}"}
        )


# -------------------------------------------------------------------
# Get my bookings (user)
# -------------------------------------------------------------------
@booking.get(
    "/my",
    response_model=BookingListPage,
    status_code=status.HTTP_200_OK
)
async def get_my_bookings(
    status: Optional[BookingStatus] = Query(None),
    upcoming: Optional[bool] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    try:
        return await get_user_bookings_service(
            db=db,
            user_id=current_user.user_id,
            status=status,
            upcoming=upcoming,
            limit=limit,
            offset=offset,
        )
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail}
        ) 
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"An unexpected error occurred: {e}"}
        )


@booking.get(
    "/salonsbystyle",
    response_model=SalonOfferListResponse,
)
async def list_salons_for_style(
    sub_service_id: str = Query(..., description="Selected style / sub service"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """
    Return salons that offer a given style (sub_service),
    enriched with price and duration.
    """
    results = await get_salons_for_style(
        db=db,
        sub_service_id=sub_service_id,
        limit=limit,
        offset=offset,
        current_user_id=current_user.user_id,
    )

    return results


@booking.get(
    "/availability",
    response_model=AvailabilityResponse,
    status_code=status.HTTP_200_OK,
)
async def get_booking_availability(
    salon_service_price_id: str = Query(...),
    stylist_id: Optional[str] = Query(None),
    start_date: date | None = Query(None),
    days: int = Query(14, ge=1, le=31),
    db: Session = Depends(get_db),
):
    return await get_availability_slots_service(
        db=db,
        salon_service_price_id=salon_service_price_id,
        stylist_id=stylist_id,
        start_date=start_date,
        days=days,
    )


@booking.get(
    "/offers/{salon_service_price_id}/stylists",
    response_model=BookingStylistOptionListResponse,
    status_code=status.HTTP_200_OK,
)
async def get_booking_stylists(
    salon_service_price_id: str,
    start_at: Optional[datetime] = Query(None),
    exclude_booking_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    return await get_booking_stylists_for_offer(
        db=db,
        salon_service_price_id=salon_service_price_id,
        start_at=start_at,
        exclude_booking_id=exclude_booking_id,
        limit=limit,
        offset=offset,
    )


# -------------------------------------------------------------------
# Get salon bookings
# -------------------------------------------------------------------
@booking.get(
    "/salon",
    response_model=BookingResponsePage,
    status_code=status.HTTP_200_OK
)
async def get_salon_bookings(
    status: Optional[BookingStatus] = Query(None),
    upcoming: Optional[bool] = Query(None),
    date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    try:
        return await get_salon_bookings_service(
            db=db,
            user_id=current_user.user_id,
            status=status,
            upcoming=upcoming,
            date=date,
            limit=limit,
            offset=offset,
        )
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail}
        ) 
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"An unexpected error occurred: {e}"}
        )


# -------------------------------------------------------------------
# Get single booking (user or salon)
# -------------------------------------------------------------------
@booking.get(
    "/{booking_id}",
    response_model=BookingResponse,
    status_code=status.HTTP_200_OK
)
async def get_booking(
    booking_id: str,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    try:
        return await get_booking_service(
            db=db,
            booking_id=booking_id,
            user_id=current_user.user_id,
        )
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail}
        ) 
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"An unexpected error occurred: {e}"}
        )


@booking.get(
    "/{booking_id}/events",
    response_model=List[BookingEventResponse],
    status_code=status.HTTP_200_OK,
)
async def get_booking_events(
    booking_id: str,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    try:
        return await get_booking_events_service(
            db=db,
            booking_id=booking_id,
            user_id=current_user.user_id,
        )
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"An unexpected error occurred: {e}"},
        )


# -------------------------------------------------------------------
# Cancel booking (user)
# -------------------------------------------------------------------
@booking.post(
    "/{booking_id}/cancel",
    response_model=BookingResponse,
    status_code=status.HTTP_200_OK
)
async def cancel_booking(
    booking_id: str,
    payload: BookingCancel,
    request: Request,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    enforce_rate_limit(
        request,
        bucket="booking:cancel",
        limit=20,
        window_seconds=300,
        user_id=current_user.user_id,
    )
    try:
        return await cancel_booking_service(
            db=db,
            booking_id=booking_id,
            user_id=current_user.user_id,
            payload=payload,
        )
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail}
        ) 
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"An unexpected error occurred: {e}"}
        )


# -------------------------------------------------------------------
# Confirm booking (salon)
# -------------------------------------------------------------------
@booking.post(
    "/{booking_id}/confirm",
    response_model=BookingResponse,
    status_code=status.HTTP_200_OK
)
async def confirm_booking(
    booking_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    enforce_rate_limit(
        request,
        bucket="booking:confirm",
        limit=30,
        window_seconds=300,
        user_id=current_user.user_id,
    )
    try:
        return await confirm_booking_service(
            db=db,
            booking_id=booking_id,
            user_id=current_user.user_id,
        )
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail}
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"An unexpected error occurred: {e}"}
        )


@booking.post(
    "/{booking_id}/assign-stylist",
    response_model=BookingResponse,
    status_code=status.HTTP_200_OK,
)
async def assign_booking_stylist(
    booking_id: str,
    payload: BookingAssignStylist,
    request: Request,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    enforce_rate_limit(
        request,
        bucket="booking:assign_stylist",
        limit=30,
        window_seconds=300,
        user_id=current_user.user_id,
    )
    try:
        return await assign_booking_stylist_service(
            db=db,
            booking_id=booking_id,
            user_id=current_user.user_id,
            stylist_id=payload.stylist_id,
        )
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"An unexpected error occurred: {e}"},
        )


# -------------------------------------------------------------------
# Reject booking (salon)
# -------------------------------------------------------------------
@booking.post(
    "/{booking_id}/reject",
    response_model=BookingResponse,
    status_code=status.HTTP_200_OK
)
async def reject_booking(
    booking_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    enforce_rate_limit(
        request,
        bucket="booking:reject",
        limit=30,
        window_seconds=300,
        user_id=current_user.user_id,
    )
    try:
        return await reject_booking_service(
            db=db,
            booking_id=booking_id,
            user_id=current_user.user_id,
        )
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail}
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"An unexpected error occurred: {e}"}
        )


# -------------------------------------------------------------------
# Complete booking (salon)
# -------------------------------------------------------------------
@booking.post(
    "/{booking_id}/complete",
    response_model=BookingResponse,
    status_code=status.HTTP_200_OK
)
async def complete_booking(
    booking_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    enforce_rate_limit(
        request,
        bucket="booking:complete",
        limit=30,
        window_seconds=300,
        user_id=current_user.user_id,
    )
    try:
        return await complete_booking_service(
            db=db,
            booking_id=booking_id,
            user_id=current_user.user_id,
        )
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail}
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"An unexpected error occurred: {e}"}
        )


# -------------------------------------------------------------------
# Mark no-show (salon)
# -------------------------------------------------------------------
@booking.post(
    "/{booking_id}/no-show",
    response_model=BookingResponse,
    status_code=status.HTTP_200_OK,
)
async def mark_no_show(
    booking_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    enforce_rate_limit(
        request,
        bucket="booking:no_show",
        limit=30,
        window_seconds=300,
        user_id=current_user.user_id,
    )
    try:
        return await mark_no_show_service(
            db=db,
            booking_id=booking_id,
            user_id=current_user.user_id,
        )
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"An unexpected error occurred: {e}"},
        )


# -------------------------------------------------------------------
# Reschedule booking (customer)
# -------------------------------------------------------------------
@booking.post(
    "/{booking_id}/reschedule",
    response_model=BookingResponse,
    status_code=status.HTTP_200_OK,
)
async def reschedule_booking(
    booking_id: str,
    payload: BookingReschedule,
    request: Request,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    enforce_rate_limit(
        request,
        bucket="booking:reschedule",
        limit=10,
        window_seconds=300,
        user_id=current_user.user_id,
    )
    try:
        return await reschedule_booking_service(
            db=db,
            booking_id=booking_id,
            user_id=current_user.user_id,
            payload=payload,
        )
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": f"An unexpected error occurred: {e}"})


# -------------------------------------------------------------------
# Leave a review (customer)
# -------------------------------------------------------------------
@booking.post(
    "/{booking_id}/review",
    response_model=BookingReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
async def leave_review(
    booking_id: str,
    payload: BookingReviewCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    enforce_rate_limit(
        request,
        bucket="booking:review",
        limit=10,
        window_seconds=300,
        user_id=current_user.user_id,
    )
    try:
        return await create_review_service(
            db=db,
            booking_id=booking_id,
            user_id=current_user.user_id,
            payload=payload,
        )
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": f"An unexpected error occurred: {e}"})


# -------------------------------------------------------------------
# Choose salon for booking
# -------------------------------------------------------------------
