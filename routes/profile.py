

from http.client import HTTPException
from typing import List
from fastapi import APIRouter, File, Form, Query, UploadFile, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from core.database import get_db
from pydantic_schemas.auth.jwt_token import TokenData
from pydantic_schemas.profile.followers_view_profile import get_salon_followers
from pydantic_schemas.profile.salon import  SalonGalleryResponse, SalonProfileResponse
from pydantic_schemas.profile.salon_config_service import SalonServiceConfigIn, SalonServiceConfigOut, SalonServiceSelectableList
from pydantic_schemas.profile.salon_view import SalonFollowersResponseSchema, SalonViewProfileResponseSchema
from pydantic_schemas.profile.settings import AccountMediaResponse, SalonContactLocationResponse, SalonContactUpdateRequest, SalonProfileResponse, SalonProfileUpdateRequest, SalonWorkingHoursResponse, SalonWorkingHoursUpdateRequest
from pydantic_schemas.profile.top_salon import TopSalonResponse
from service.auth.JWT.oauth2 import get_current_user
from service.profile.salon import profile_salon
from service.profile.salon_folow_unfollow import follow_salon, unfollow_salon
from service.profile.salon_service_config import list_selectable_services
from service.profile.salon_view import view_salon_profile
from service.profile.settings.contact_location import update_salon_contact_
from service.profile.settings.salon_gallery import manage_salon_gallery_
from service.profile.settings.salon_profile import update_salon_profile_
from service.profile.settings.salon_working_hours import update_salon_working_hours_
from service.profile.settings.upload_account_media import upload_account_media_
from service.profile.top_salon import get_top_salons


profile = APIRouter(
    prefix='/profile',
    tags=['Profile']
)

# -------------------------------------------------------------------
#                                Get

# -------------------------------------------------------------------
# Get Salon Profle
# -------------------------------------------------------------------
@profile.get('/salon',  status_code=status.HTTP_200_OK)
async def salon_profile(db: Session = Depends(get_db), current_user: TokenData = Depends(get_current_user)):
    user_id = current_user.user_id
    
    # Let FastAPI handle the response_model serialization
    # If profile_salon returns a dict, FastAPI will validate it against SalonProfileResponse
    return await profile_salon(db=db, user=user_id)



# -------------------------------------------------------------------
# Salon Services and other configured by salon 
# -------------------------------------------------------------------
@profile.get(
    "/salon/services",
    # response_model=SalonServiceSelectableList,
    status_code=status.HTTP_200_OK,
)
def list_services_for_selection(
    q: str | None = Query(default=None, max_length=100),
    include_archived: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """
    Page 1:
    - list platform services/sub-services
    - mark which ones are already configured by this salon
    """
    # if not getattr(current_user, "salon", None):
    #     raise HTTPException(
    #         status_code=status.HTTP_404_NOT_FOUND,
    #         detail="Salon not found",
    #     )


    # NOTE: router-only. Business logic goes into service layer.
    return list_selectable_services(
        db=db,
        salon_id=current_user.user_id,
        q=q,
        include_archived=include_archived,
        limit=limit,
        offset=offset,
    )

# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Salon Create Congigured Services
# -------------------------------------------------------------------
@profile.post(
    "/salon/services",
    response_model=SalonServiceConfigOut,
    status_code=status.HTTP_201_CREATED,
)
def create_salon_service_route(
    payload: SalonServiceConfigIn,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """
    Configure a service for the first time (CREATE).
    """
    salon = getattr(current_user, "salon", None)
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found",
        )

    # Router stays thin – service layer will:
    # - validate service / sub-service
    # - ensure not already configured
    # - create SalonServicePrice
    # - sync benefits, products, stylists
    #
    # return create_salon_service(
    #     db=db,
    #     salon=salon,
    #     payload=payload,
    # )

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Create salon service not implemented yet",
    )
    
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Salon Update Configured Services
# -------------------------------------------------------------------
@profile.put(
    "/salon/services/{salon_service_price_id}",
    response_model=SalonServiceConfigOut,
    status_code=status.HTTP_200_OK,
)
def update_salon_service_route(
    salon_service_price_id: str,
    payload: SalonServiceConfigIn,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """
    Update an already configured salon service.
    """
    salon = getattr(current_user, "salon", None)
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found",
        )

    # Router stays thin – service layer will:
    # - fetch service by id + salon ownership
    # - update core fields
    # - resync benefits, products, stylists
    # - handle status transitions
    #
    # return update_salon_service(
    #     db=db,
    #     salon=salon,
    #     salon_service_price_id=salon_service_price_id,
    #     payload=payload,
    # )

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Update salon service not implemented yet",
    )

# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Public: View Salon Profile by Username
# -------------------------------------------------------------------
@profile.get(
    "/salon/{salon_id}",
    response_model=SalonViewProfileResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def view_salon_by_username(
    salon_id: str,
    db: Session = Depends(get_db),
    current_user: TokenData | None = Depends(get_current_user),
):
    """
    Public salon profile view.
    - If authenticated → viewer-aware (follow/block state)
    - If not authenticated → viewer defaults applied
    """
    viewer_id = current_user.user_id if current_user else None

    return await view_salon_profile(
        salon_id=salon_id,
        db=db,
        viewer_id=viewer_id,
    )

# -------------------------------------------------------------------
# Public: Salon Followers
# -------------------------------------------------------------------
@profile.get(
    "/salon/{salon_id}/followers",
    response_model=SalonFollowersResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def salon_followers(
    salon_id: str,
    limit: int = Query(20, le=50),
    cursor: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: TokenData | None = Depends(get_current_user),
):
    viewer_id = current_user.user_id if current_user else None

    return get_salon_followers(
        db=db,
        salon_id=salon_id,
        viewer_id=viewer_id,
        limit=limit,
        cursor=cursor,
    )
    
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Follow / Unfollow Salon
# -------------------------------------------------------------------
@profile.post("/salon/{salon_id}/follow")
async def follow(
    salon_id: str,
    db: Session = Depends(get_db),
    user: TokenData =Depends(get_current_user),
):
    await follow_salon(db=db, salon_id=salon_id, user_id=user.user_id)
    return {"success": True}


@profile.delete("/salon/{salon_id}/follow")
async def unfollow(
    salon_id: str,
    db: Session = Depends(get_db),
    user: TokenData = Depends(get_current_user),
):
    await unfollow_salon(db=db, salon_id=salon_id, user_id=user.user_id)
    return {"success": True}

# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Top Salons
# -------------------------------------------------------------------
@profile.get("/top", response_model=TopSalonResponse)
async def fetch_top_salons(
    limit: int = Query(10, le=20),
    db: Session = Depends(get_db),
):
    try:
        # Just call the service and return
        return get_top_salons(db, limit)
        
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
        
# -------------------------------------------------------------------
# Authenticated: Salon Profile Settings
# -------------------------------------------------------------------
@profile.patch(
    "/upload_account_media",
    response_model=AccountMediaResponse
)
async def upload_account_media(
    profile_image: UploadFile | None = File(None),
    cover_ads: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    return await upload_account_media_(
        user_id=current_user.user_id,
        profile_image=profile_image,
        cover_ads=cover_ads,
        db=db,
    )
    
# -------------------------------------------------------------------



# -------------------------------------------------------------------
# Authenticated: Salon Profile Settings - Update Profile, Contact, Working Hours, Gallery
# -------------------------------------------------------------------
@profile.patch(
    "/salon_profile",
    response_model=SalonProfileResponse,
)
async def update_salon_profile(
    payload: SalonProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await update_salon_profile_(
        user_id=current_user.user_id,
        payload=payload,
        db=db,
    )

# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Authenticated: Salon Profile Settings - Update Contact Location
# -------------------------------------------------------------------
@profile.patch(
    "/contact",
    response_model=SalonContactLocationResponse,
)
async def update_salon_contact(
    payload: SalonContactUpdateRequest,
    db: Session = Depends(get_db), current_user: TokenData = Depends(get_current_user),
):
    return await update_salon_contact_(
        user_id=current_user.user_id,
        payload=payload,
        db=db,
    )
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Authenticated: Salon Profile Settings - Update Working Hours
# -------------------------------------------------------------------
@profile.put(
    "/working_hours",
    response_model=SalonWorkingHoursResponse,
)
async def update_working_hours(
    payload: SalonWorkingHoursUpdateRequest,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    return await update_salon_working_hours_(
        user_id=current_user.user_id,
        payload=payload,
        db=db,
    )

# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Authenticated: Salon Profile Settings - Manage Gallery
# -------------------------------------------------------------------
@profile.patch(
    "/salon_gallery",
    response_model=List[SalonGalleryResponse],
)
async def update_gallery(
    # Optional files for adding
    files: List[UploadFile] = File(default=[]),
    # Optional IDs for deleting (sent as a comma-separated string or multiple form fields)
    delete_ids: List[str] = Form(default=[]),
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user),
):
    return await manage_salon_gallery_(
        db=db,
        user_id=current_user.user_id,
        files=files,
        delete_ids=delete_ids,
    )
    
# -------------------------------------------------------------------
