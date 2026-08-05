"""Provides the Profile API route module for the backend application."""



from datetime import date
from typing import List, Optional
from fastapi import HTTPException, APIRouter, File, Form, Query, UploadFile, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from core.database import get_db
from pydantic_schemas.auth.jwt_token import TokenData
from pydantic_schemas.profile.config_service_salon import MessageResponse, SalonServiceConfigDetailResponse
from pydantic_schemas.profile.followers_view_profile import get_salon_followers
from pydantic_schemas.profile.insights import ProfileInsightsResponse
from pydantic_schemas.profile.salon import  SalonGalleryResponse, SalonProfileResponse
from pydantic_schemas.profile.trust import BusinessDocumentUploadResponse, TrustStatusResponse
from pydantic_schemas.profile.salon_config_service import SalonServiceConfigIn, SalonServiceConfigOut
from pydantic_schemas.profile.salon_stylists import SalonStylistCreate, SalonStylistListOut, SalonStylistOut, SalonStylistOutSimple, SalonStylistUpdate, UserSearchListOut
from pydantic_schemas.profile.salon_view import SalonFollowersResponseSchema, SalonViewProfileResponseSchema
from pydantic_schemas.profile.salon_activity import ActivityFeedResponse
from pydantic_schemas.profile.settings import AccountMediaResponse, SalonAvailabilityOverrideIn, SalonAvailabilityOverrideListResponse, SalonAvailabilityOverrideOut, SalonContactLocationResponse, SalonContactUpdateRequest, SalonProfileResponse, SalonProfileUpdateRequest, SalonWorkingHoursResponse, SalonWorkingHoursUpdateRequest
from pydantic_schemas.profile.top_salon import TopSalonResponse
from service.auth.JWT.oauth2 import get_current_user
from service.auth.permissions import SalonPrincipal, UserPrincipal, require_active_user, require_salon_owner
from service.account.audit import record_audit_event
from service.profile.configure_service_salon import get_salon_services_for_config
from service.profile.salon import profile_salon
from service.profile.salon_config_service import create_salon_service, update_salon_service
from service.profile.salon_create_stylists import SalonStylistService
from service.profile.salon_folow_unfollow import follow_salon, unfollow_salon
from service.profile.insights import get_profile_insights, record_salon_service_tap
from service.profile.trust import get_trust_status, upload_business_document
from service.profile.salon_service_config import list_selectable_services
from service.profile.salon_view import view_salon_profile
from service.profile.settings.contact_location import update_salon_contact_
from service.profile.settings.availability_calendar import delete_availability_override_, list_availability_overrides_, upsert_availability_override_
from service.profile.settings.salon_gallery import manage_salon_gallery_
from service.profile.settings.salon_profile import update_salon_profile_
from service.profile.settings.salon_working_hours import update_salon_working_hours_
from service.profile.settings.upload_account_media import upload_account_media_
from service.profile.salon_activity import get_salon_activity
from models.profile.salon import Salon
from service.profile.top_salon import get_top_salons


profile = APIRouter(
    prefix='/profile',
    tags=['Profile']
)

# -------------------------------------------------------------------
#                                Get

# -------------------------------------------------------------------
@profile.get(
    "/insights",
    response_model=ProfileInsightsResponse,
    status_code=status.HTTP_200_OK,
)
def profile_insights(
    db: Session = Depends(get_db),
    principal: UserPrincipal = Depends(require_active_user),
):
    return get_profile_insights(db=db, principal=principal)


@profile.get(
    "/trust",
    response_model=TrustStatusResponse,
    status_code=status.HTTP_200_OK,
)
def profile_trust_status(
    db: Session = Depends(get_db),
    principal: UserPrincipal = Depends(require_active_user),
):
    return get_trust_status(db=db, principal=principal)


@profile.post(
    "/salon/trust/business-document",
    response_model=BusinessDocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def salon_business_document_upload(
    document: UploadFile = File(...),
    document_type: str = Form(default="business_document"),
    db: Session = Depends(get_db),
    salon_owner: SalonPrincipal = Depends(require_salon_owner),
):
    return await upload_business_document(
        db=db,
        salon_owner=salon_owner,
        document=document,
        document_type=document_type,
    )


@profile.post(
    "/salon/{salon_id}/service-tap/{salon_service_price_id}",
    status_code=status.HTTP_200_OK,
)
def salon_service_tap(
    salon_id: str,
    salon_service_price_id: str,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    return record_salon_service_tap(
        db=db,
        salon_id=salon_id,
        salon_service_price_id=salon_service_price_id,
        user_id=current_user.user_id,
    )


# -------------------------------------------------------------------
# Get Salon Profle
# -------------------------------------------------------------------
@profile.get('/salon',  status_code=status.HTTP_200_OK)
async def salon_profile(
    db: Session = Depends(get_db),
    salon_owner: SalonPrincipal = Depends(require_salon_owner),
):
    user_id = salon_owner.user_id
    
    # Let FastAPI handle the response_model serialization
    # If profile_salon returns a dict, FastAPI will validate it against SalonProfileResponse
    return await profile_salon(db=db, user=user_id)



# -------------------------------------------------------------------
# Salon Activity Feed
# -------------------------------------------------------------------
@profile.get(
    "/salon/activity",
    response_model=ActivityFeedResponse,
    status_code=status.HTTP_200_OK,
)
async def salon_activity_feed_owner(
    limit: int = Query(30, ge=1, le=50),
    cursor: str | None = Query(None),
    db: Session = Depends(get_db),
    salon_owner: SalonPrincipal = Depends(require_salon_owner),
):
    """Owner-only feed: resolves the caller's salon and returns full activity."""
    return await get_salon_activity(
        salon_id=salon_owner.salon_id,
        viewer_user_id=salon_owner.user_id,
        db=db,
        limit=limit,
        cursor=cursor,
    )


@profile.get(
    "/salon/{salon_id}/activity",
    response_model=ActivityFeedResponse,
    status_code=status.HTTP_200_OK,
)
async def salon_activity_feed_by_id(
    salon_id: str,
    limit: int = Query(30, ge=1, le=50),
    cursor: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Viewer-aware feed. Owner sees everything; others see public events only."""
    return await get_salon_activity(
        salon_id=salon_id,
        viewer_user_id=current_user.user_id,
        db=db,
        limit=limit,
        cursor=cursor,
    )
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Get Service those configured and not
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
    salon_owner: SalonPrincipal = Depends(require_salon_owner),
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


    # NOTE: profile-only. Business logic goes into service layer.
    return list_selectable_services(
        db=db,
        salon_id=salon_owner.user_id,
        q=q,
        include_archived=include_archived,
        limit=limit,
        offset=offset,
    )

# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Configure Salon Services (Create)
# -------------------------------------------------------------------
@profile.post(
    "/salon/services",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_salon_service_route(
    payload: SalonServiceConfigIn,
    db: Session = Depends(get_db),
    salon_owner: SalonPrincipal = Depends(require_salon_owner),
):
    """
    Configure a service for the first time (CREATE).
    """
    

    # profile stays thin – service layer will:
    # - validate service / sub-service
    # - ensure not already configured
    # - create SalonServicePrice
    # - sync benefits, products, stylists
    #
    
    return create_salon_service(
        db=db,
        salon=salon_owner.user_id,
        payload=payload,
    )
    
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Salon Update Configured Services
# -------------------------------------------------------------------
@profile.put(
    "/salon/services/{salon_service_price_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
def update_salon_service_route(
    salon_service_price_id: str,
    payload: SalonServiceConfigIn,
    db: Session = Depends(get_db),
    salon_owner: SalonPrincipal = Depends(require_salon_owner),
):
    """
    Update an already configured salon service.
    """
    

    # profile stays thin – service layer will:
    # - fetch service by id + salon ownership
    # - update core fields
    # - resync benefits, products, stylists
    # - handle status transitions
    #
    return update_salon_service(
        db=db,
        salon=salon_owner.user_id,
        salon_service_price_id=salon_service_price_id,
        payload=payload,
    )

# -------------------------------------------------------------------


# ----------------------------------------------------------------
# Get single service configuration (create + edit UI)
# ----------------------------------------------------------------
@profile.get(
    "/salon/services/{service_id}/sub/{sub_service_id}/configure",
    response_model=SalonServiceConfigDetailResponse,
    status_code=status.HTTP_200_OK,
)
def get_salon_service_config(
    service_id: str,
    sub_service_id: str,
    db: Session = Depends(get_db),
    salon_owner: SalonPrincipal = Depends(require_salon_owner),
):
    """
    Layer 2:
    - Returns details for ONE service + sub-service
    - Includes config if already configured
    - Used by Create & Update UI
    """

    salon_user_id = salon_owner.user_id

    if not salon_user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found",
        )

    return get_salon_services_for_config(
        db=db,
        salon_user_id=salon_user_id,
        service_id=service_id,
        sub_service_id=sub_service_id,
    )

# ----------------------------------------------------------------


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
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    try:
        # Just call the service and return
        return get_top_salons(
            db,
            limit,
            offset,
            exclude_user_id=current_user.user_id,
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
    cover_position_x: float | None = Form(None),
    cover_position_y: float | None = Form(None),
    db: Session = Depends(get_db),
    salon_owner: SalonPrincipal = Depends(require_salon_owner),
):
    result = await upload_account_media_(
        user_id=salon_owner.user_id,
        profile_image=profile_image,
        cover_ads=cover_ads,
        cover_position_x=cover_position_x,
        cover_position_y=cover_position_y,
        db=db,
    )
    record_audit_event(
        db,
        user_id=salon_owner.user_id,
        event_type="profile_updated",
        title="Profile media updated",
        description="Salon profile photo or cover image was updated.",
        metadata={"section": "salon_media"},
    )
    return result
    
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
    salon_owner: SalonPrincipal = Depends(require_salon_owner),
):
    result = await update_salon_profile_(
        user_id=salon_owner.user_id,
        payload=payload,
        db=db,
    )
    record_audit_event(
        db,
        user_id=salon_owner.user_id,
        event_type="profile_updated",
        title="Profile updated",
        description="Salon profile details were updated.",
        metadata={"section": "salon_profile"},
    )
    return result

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
    db: Session = Depends(get_db),
    salon_owner: SalonPrincipal = Depends(require_salon_owner),
):
    result = await update_salon_contact_(
        user_id=salon_owner.user_id,
        payload=payload,
        db=db,
    )
    record_audit_event(
        db,
        user_id=salon_owner.user_id,
        event_type="profile_updated",
        title="Contact and location updated",
        description="Salon contact or location details were updated.",
        metadata={"section": "salon_contact"},
    )
    return result
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
    salon_owner: SalonPrincipal = Depends(require_salon_owner),
):
    result = await update_salon_working_hours_(
        user_id=salon_owner.user_id,
        payload=payload,
        db=db,
    )
    record_audit_event(
        db,
        user_id=salon_owner.user_id,
        event_type="working_hours_changed",
        title="Working hours changed",
        description="Salon weekly working hours were updated.",
        metadata={"section": "working_hours"},
    )
    return result

# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Authenticated: Salon Profile Settings - Availability Calendar
# -------------------------------------------------------------------
@profile.get(
    "/availability-overrides",
    response_model=SalonAvailabilityOverrideListResponse,
)
async def list_availability_overrides(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: Session = Depends(get_db),
    salon_owner: SalonPrincipal = Depends(require_salon_owner),
):
    return await list_availability_overrides_(
        user_id=salon_owner.user_id,
        db=db,
        start_date=start_date,
        end_date=end_date,
    )


@profile.put(
    "/availability-overrides",
    response_model=SalonAvailabilityOverrideOut,
)
async def upsert_availability_override(
    payload: SalonAvailabilityOverrideIn,
    db: Session = Depends(get_db),
    salon_owner: SalonPrincipal = Depends(require_salon_owner),
):
    return await upsert_availability_override_(
        user_id=salon_owner.user_id,
        payload=payload,
        db=db,
    )


@profile.delete(
    "/availability-overrides/{override_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_availability_override(
    override_id: str,
    db: Session = Depends(get_db),
    salon_owner: SalonPrincipal = Depends(require_salon_owner),
):
    await delete_availability_override_(
        user_id=salon_owner.user_id,
        override_id=override_id,
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
    gallery_order: str | None = Form(None),
    gallery_categories: str | None = Form(None),
    new_file_categories: str | None = Form(None),
    db: Session = Depends(get_db), 
    salon_owner: SalonPrincipal = Depends(require_salon_owner),
):
    result = await manage_salon_gallery_(
        db=db,
        user_id=salon_owner.user_id,
        files=files,
        delete_ids=delete_ids,
        gallery_order=gallery_order,
        gallery_categories=gallery_categories,
        new_file_categories=new_file_categories,
    )
    record_audit_event(
        db,
        user_id=salon_owner.user_id,
        event_type="gallery_updated",
        title="Gallery updated",
        description="Salon gallery images were added or removed.",
        metadata={
            "section": "salon_gallery",
            "added_count": len(files),
            "removed_count": len(delete_ids),
        },
    )
    return result
    
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# CREATE STYLIST
# -------------------------------------------------------------------
@profile.post(
    "/stylist",
    response_model=SalonStylistOutSimple,
    status_code=status.HTTP_201_CREATED,
)
def create_salon_stylist(
    payload: SalonStylistCreate,
    db: Session = Depends(get_db),
    salon_owner: SalonPrincipal = Depends(require_salon_owner),
):
    result = SalonStylistService(db, user_id=salon_owner.user_id).create(payload)
    record_audit_event(
        db,
        user_id=salon_owner.user_id,
        event_type="stylist_added",
        title="Stylist added",
        description="A stylist was added to the salon team.",
        metadata={"stylist_id": getattr(result, "id", None)},
    )
    return result


# -------------------------------------------------------------------
# LIST (optional filters + pagination)
# -------------------------------------------------------------------
@profile.get("/stylists", response_model=SalonStylistListOut)
def list_salon_stylists(
    salon_owner: SalonPrincipal = Depends(require_salon_owner),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return SalonStylistService(db, user_id=salon_owner.user_id).list_for_salon(
        # user_id=user_id.user_id,
        limit=limit,
        offset=offset,
    )
 
# -------------------------------------------------------------------
# SEARCH USERS TO ADD AS STYLISTS (by name or email, with pagination)
# -------------------------------------------------------------------   
@profile.get("/stylists/search-users", response_model=UserSearchListOut)
def search_potential_stylists(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    salon_owner: SalonPrincipal = Depends(require_salon_owner),
):
    service = SalonStylistService(db, user_id=salon_owner.user_id)
    results = service.search_users_to_add(query=q, limit=limit)
    
    return {
        "items": results,
        "query": q,
        "count": len(results)
    }

# -------------------------------------------------------------------
# GET ONE STYLIST (for edit form, or just to view details)
# -------------------------------------------------------------------
@profile.get("/stylist/{stylist_id}", response_model=SalonStylistOut)
def get_one_salon_stylist(
    stylist_id: str,
    db: Session = Depends(get_db),
    salon_owner: SalonPrincipal = Depends(require_salon_owner),
):
    """
    Fetch details for a specific stylist.
    Used to populate the 'Edit Stylist' screen.
    """
    service = SalonStylistService(db, user_id=salon_owner.user_id)
    return service.get_stylist(stylist_id)


# -------------------------------------------------------------------
# UPDATE (PATCH) STYLIST - partial update, only fields sent will be updated
# -------------------------------------------------------------------
@profile.patch("/stylist/{stylist_id}", response_model=SalonStylistOut)
def update_salon_stylist(
    stylist_id: str,
    payload: SalonStylistUpdate,
    db: Session = Depends(get_db),
    salon_owner: SalonPrincipal = Depends(require_salon_owner),
):
    """
    Update stylist details (title, bio, active status).
    Only the salon owner can perform this.
    """
    service = SalonStylistService(db, user_id=salon_owner.user_id)
    result = service.update_stylist(stylist_id, payload)
    record_audit_event(
        db,
        user_id=salon_owner.user_id,
        event_type="stylist_updated",
        title="Stylist updated",
        description="A stylist profile or permissions were updated.",
        metadata={"stylist_id": stylist_id},
    )
    return result


# -------------------------------------------------------------------
# REMOVE STYLIST (soft delete by default)
# -------------------------------------------------------------------
@profile.delete(
    "/stylist/{stylist_id}", 
    status_code=status.HTTP_204_NO_CONTENT
)
def remove_salon_stylist(
    stylist_id: str,
    db: Session = Depends(get_db),
    salon_owner: SalonPrincipal = Depends(require_salon_owner),
):
    """
    Removes a stylist from the owner's salon.
    'stylist_id' is the unique ID of the SalonStylist record.
    """
    service = SalonStylistService(db, user_id=salon_owner.user_id)
    service.remove_stylist(stylist_id)
    record_audit_event(
        db,
        user_id=salon_owner.user_id,
        event_type="stylist_removed",
        title="Stylist removed",
        description="A stylist was removed from the salon team.",
        metadata={"stylist_id": stylist_id},
    )
    return None # 204 No Content doesn't return a body
