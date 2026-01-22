from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional

from core.database import get_db
from core.enumeration import BookingStatus

from pydantic_schemas.auth.jwt_token import TokenData
from pydantic_schemas.booking.booking import (
    BookingCreate,
    BookingResponse,
    BookingCancel,
    BookingListItem,
)

from pydantic_schemas.booking.choose_salon import SalonOfferListResponse
from service.auth.JWT.oauth2 import get_current_user
from service.booking.booking import cancel_booking_service, complete_booking_service, confirm_booking_service, create_booking_service, get_booking_service, get_salon_bookings_service, get_salons_for_style, get_user_bookings_service, reject_booking_service


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
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    print("BOOKING PAYLOAD:", payload)
    print("USER:", current_user.user_id)
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
    response_model=List[BookingListItem],
    status_code=status.HTTP_200_OK
)
async def get_my_bookings(
    status: Optional[BookingStatus] = Query(None),
    upcoming: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    try:
        return await get_user_bookings_service(
            db=db,
            user_id=current_user.user_id,
            status=status,
            upcoming=upcoming,
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
    db: Session = Depends(get_db),
):
    """
    Return salons that offer a given style (sub_service),
    enriched with price and duration.
    """
    results = await get_salons_for_style(
        db=db,
        sub_service_id=sub_service_id,
    )

    return {"results": results}



# -------------------------------------------------------------------
# Get salon bookings
# -------------------------------------------------------------------
@booking.get(
    "/salon",
    response_model=List[BookingResponse],
    status_code=status.HTTP_200_OK
)
async def get_salon_bookings(
    status: Optional[BookingStatus] = Query(None),
    upcoming: Optional[bool] = Query(None),
    date: Optional[str] = Query(None, description="YYYY-MM-DD"),
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
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
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
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
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
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
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
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
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
# Choose salon for booking
# -------------------------------------------------------------------

