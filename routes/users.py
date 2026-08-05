"""Provides the Users API route module for the backend application."""

import time
from collections import deque
from threading import Lock

from fastapi import APIRouter, Query, Request, status, HTTPException
from fastapi.params import Depends
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.database import get_db
from models.auth.user import User
from pydantic_schemas.auth.jwt_token import TokenData
from pydantic_schemas.account.settings import AccountSettingsResponse, AccountSettingsUpdate
from pydantic_schemas.account.audit import AuditEventListResponse
from pydantic_schemas.account.profile_settings import (
    AccountDataExport,
    CustomerBeautyPreferences,
    CustomerBlockedAccounts,
    CustomerProfilePreviewVisibility,
    CustomerRecommendationControls,
    SalonBookingRules,
    SalonCampaignDrafts,
    SalonCampaignHistory,
    SalonTeamPermissions,
)
from pydantic_schemas.account.profile_completion import ProfileCompletionResponse
from pydantic_schemas.customer.following import MyFollowingResponse
from pydantic_schemas.customer.profile import CustomerProfileResponse, CustomerProfileUpdate
from pydantic_schemas.mute import MuteListResponse, MuteResponse, MuteTargetType
from pydantic_schemas.profile.notification_preferences import (
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
)
from pydantic_schemas.users.user_select_service import UserSelectServicesResponse
from pydantic_schemas.users.device_token import DeviceTokenListResponse, DeviceTokenResponse, DeviceTokenUpsert
from service.auth.JWT.oauth2 import get_current_user
from service.account.settings import get_account_settings, update_account_settings
from service.account.audit import list_audit_events, record_audit_event
from service.account.profile_settings import (
    get_customer_account_data_export,
    get_customer_beauty_preferences,
    get_customer_blocked_accounts,
    get_customer_profile_preview_visibility,
    get_customer_recommendation_controls,
    get_salon_booking_rules,
    get_salon_campaign_drafts,
    get_salon_campaign_history,
    get_salon_team_permissions,
    update_customer_beauty_preferences,
    update_customer_blocked_accounts,
    update_customer_profile_preview_visibility,
    update_customer_recommendation_controls,
    update_salon_booking_rules,
    update_salon_campaign_drafts,
    update_salon_campaign_history,
    update_salon_team_permissions,
)
from service.account.profile_completion import get_profile_completion
from service.customer.following import get_my_following
from service.customer.profile import get_customer_profile_, update_customer_profile_
from service.search.users import recommend_user, search_user
from service.notification.push import push_service_status, send_test_push_to_user
from service.users.mutes import list_mutes, mute_target, unmute_target
from service.users.device_tokens import deactivate_device_token, list_device_tokens, upsert_device_token
from service.users.notification_preferences import (
    get_preferences as get_notification_preferences_,
    update_preferences as update_notification_preferences_,
)
from service.users.user_select_services import user_select_services_
from service.users.saved import (
    list_saved_salons,
    list_saved_services,
    list_saved_styles,
    toggle_saved_salon,
    toggle_saved_service,
    toggle_saved_style,
)


users = APIRouter(
    prefix="/users",
    tags=["Users"], # Add your dependencies here
)





# ---------------------------------------------------
# Customer Profile Endpoints
# ---------------------------------------------------

@users.get("/me/profile", response_model=CustomerProfileResponse)
async def get_my_profile(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return get_customer_profile_(current_user.user_id, db, viewer_user_id=current_user.user_id)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": str(e)})


@users.put("/me/profile", response_model=CustomerProfileResponse)
async def update_my_profile(
    data: CustomerProfileUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = update_customer_profile_(current_user.user_id, data, db)
        record_audit_event(
            db,
            user_id=current_user.user_id,
            event_type="profile_updated",
            title="Profile updated",
            description="Customer profile details were updated.",
            metadata={"section": "customer_profile"},
        )
        return result
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": str(e)})


@users.get("/me/following", response_model=MyFollowingResponse)
async def get_my_following_list(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return get_my_following(
            current_user.user_id,
            db,
            limit=limit,
            offset=offset,
        )
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": str(e)})




# ---------------------------------------------------
# Device tokens for push notifications
# ---------------------------------------------------

@users.get("/me/device-tokens", response_model=DeviceTokenListResponse)
def get_my_device_tokens(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_device_tokens(db=db, user_id=current_user.user_id)


@users.put("/me/device-tokens", response_model=DeviceTokenResponse, status_code=200)
def register_my_device_token(
    payload: DeviceTokenUpsert,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return upsert_device_token(db=db, user_id=current_user.user_id, payload=payload)


@users.get("/me/push-status")
def get_my_push_status(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return push_service_status(db=db, user_id=current_user.user_id)


@users.post("/me/push-test")
def send_my_push_test(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return send_test_push_to_user(db=db, user_id=current_user.user_id)


@users.delete("/me/device-tokens/{device_id}", status_code=200)
def delete_my_device_token(
    device_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return deactivate_device_token(db=db, user_id=current_user.user_id, device_id=device_id)


# ---------------------------------------------------
# Mute controls
# ---------------------------------------------------

@users.get("/me/mutes", response_model=MuteListResponse)
def get_my_mutes(
    target_type: MuteTargetType | None = Query(None),
    q: str | None = Query(None, max_length=120),
    sort: str = Query("newest", pattern="^(newest|type)$"),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_mutes(
        db=db,
        user_id=current_user.user_id,
        target_type=target_type,
        q=q,
        sort=sort,
    )


@users.post("/me/mutes/{target_type}/{target_id}", response_model=MuteResponse, status_code=200)
def mute_target_route(
    target_type: MuteTargetType,
    target_id: str,
    reason: str | None = Query(None, max_length=255),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return mute_target(
        db=db,
        user_id=current_user.user_id,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
    )


@users.delete("/me/mutes/{target_type}/{target_id}", status_code=200)
def unmute_target_route(
    target_type: MuteTargetType,
    target_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return unmute_target(
        db=db,
        user_id=current_user.user_id,
        target_type=target_type,
        target_id=target_id,
    )


# ---------------------------------------------------
# Saved items
# ---------------------------------------------------

@users.get("/me/saved/salons")
def get_my_saved_salons(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_saved_salons(user_id=current_user.user_id, db=db)


@users.post("/me/saved/salons/{salon_id}", status_code=200)
def save_or_unsave_salon(
    salon_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return toggle_saved_salon(user_id=current_user.user_id, salon_id=salon_id, db=db)


@users.get("/me/saved/services")
def get_my_saved_services(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_saved_services(user_id=current_user.user_id, db=db)


@users.post("/me/saved/services/{service_id}", status_code=200)
def save_or_unsave_service(
    service_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return toggle_saved_service(user_id=current_user.user_id, service_id=service_id, db=db)


@users.get("/me/saved/styles")
def get_my_saved_styles(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_saved_styles(user_id=current_user.user_id, db=db)


@users.post("/me/saved/styles/{style_id}", status_code=200)
def save_or_unsave_style(
    style_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return toggle_saved_style(user_id=current_user.user_id, style_id=style_id, db=db)


# ---------------------------------------------------
# Synced account settings
# ---------------------------------------------------

@users.get(
    "/me/account-settings",
    response_model=AccountSettingsResponse,
)
def get_my_account_settings(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_account_settings(db, current_user.user_id)


@users.patch(
    "/me/account-settings",
    response_model=AccountSettingsResponse,
)
def update_my_account_settings(
    payload: AccountSettingsUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_account_settings(db, current_user.user_id, payload)


@users.get("/me/audit-log", response_model=AuditEventListResponse)
def get_my_audit_log(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_audit_events(
        db,
        user_id=current_user.user_id,
        limit=limit,
        offset=offset,
    )


def _current_user_row(db: Session, current_user: TokenData) -> User:
    user = db.query(User).filter(User.id == current_user.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


@users.get("/me/customer/beauty-preferences", response_model=CustomerBeautyPreferences)
def get_my_customer_beauty_preferences(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_customer_beauty_preferences(db, current_user.user_id)


@users.patch("/me/customer/beauty-preferences", response_model=CustomerBeautyPreferences)
def update_my_customer_beauty_preferences(
    payload: CustomerBeautyPreferences,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_customer_beauty_preferences(db, current_user.user_id, payload)


@users.get("/me/customer/recommendation-controls", response_model=CustomerRecommendationControls)
def get_my_customer_recommendation_controls(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_customer_recommendation_controls(db, current_user.user_id)


@users.patch("/me/customer/recommendation-controls", response_model=CustomerRecommendationControls)
def update_my_customer_recommendation_controls(
    payload: CustomerRecommendationControls,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_customer_recommendation_controls(db, current_user.user_id, payload)


@users.get("/me/customer/profile-preview-visibility", response_model=CustomerProfilePreviewVisibility)
def get_my_customer_profile_preview_visibility(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_customer_profile_preview_visibility(db, current_user.user_id)


@users.patch("/me/customer/profile-preview-visibility", response_model=CustomerProfilePreviewVisibility)
def update_my_customer_profile_preview_visibility(
    payload: CustomerProfilePreviewVisibility,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_customer_profile_preview_visibility(db, current_user.user_id, payload)


@users.get("/me/customer/blocked-accounts", response_model=CustomerBlockedAccounts)
def get_my_customer_blocked_accounts(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_customer_blocked_accounts(db, current_user.user_id)


@users.put("/me/customer/blocked-accounts", response_model=CustomerBlockedAccounts)
def update_my_customer_blocked_accounts(
    payload: CustomerBlockedAccounts,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_customer_blocked_accounts(db, current_user.user_id, payload)


@users.get("/me/customer/account-data", response_model=AccountDataExport)
def export_my_customer_account_data(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_customer_account_data_export(db, _current_user_row(db, current_user))


@users.get("/me/profile-completion", response_model=ProfileCompletionResponse)
def get_my_profile_completion(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_profile_completion(db, _current_user_row(db, current_user))


@users.get("/me/salon/booking-rules", response_model=SalonBookingRules)
def get_my_salon_booking_rules(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_salon_booking_rules(db, _current_user_row(db, current_user))


@users.patch("/me/salon/booking-rules", response_model=SalonBookingRules)
def update_my_salon_booking_rules(
    payload: SalonBookingRules,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = _current_user_row(db, current_user)
    result = update_salon_booking_rules(db, user, payload)
    record_audit_event(
        db,
        user_id=user.id,
        event_type="booking_rules_changed",
        title="Booking rules changed",
        description="Salon booking rules were updated.",
        metadata={"section": "salon_booking_rules"},
    )
    return result


@users.get("/me/salon/campaign-drafts", response_model=SalonCampaignDrafts)
def get_my_salon_campaign_drafts(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_salon_campaign_drafts(db, _current_user_row(db, current_user))


@users.put("/me/salon/campaign-drafts", response_model=SalonCampaignDrafts)
def update_my_salon_campaign_drafts(
    payload: SalonCampaignDrafts,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = _current_user_row(db, current_user)
    before = get_salon_campaign_drafts(db, user)
    result = update_salon_campaign_drafts(db, user, payload)
    event_title = "Campaign drafts updated"
    event_type = "campaign_drafts_updated"
    if len(result.drafts) > len(before.drafts):
        event_title = "Campaign draft created"
        event_type = "campaign_draft_created"
    record_audit_event(
        db,
        user_id=user.id,
        event_type=event_type,
        title=event_title,
        description="Salon campaign draft list changed.",
        metadata={"draft_count": len(result.drafts)},
    )
    return result


@users.get("/me/salon/campaign-history", response_model=SalonCampaignHistory)
def get_my_salon_campaign_history(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_salon_campaign_history(db, _current_user_row(db, current_user))


@users.put("/me/salon/campaign-history", response_model=SalonCampaignHistory)
def update_my_salon_campaign_history(
    payload: SalonCampaignHistory,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_salon_campaign_history(db, _current_user_row(db, current_user), payload)


@users.get("/me/salon/team-permissions", response_model=SalonTeamPermissions)
def get_my_salon_team_permissions(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_salon_team_permissions(db, _current_user_row(db, current_user))


@users.put("/me/salon/team-permissions", response_model=SalonTeamPermissions)
def update_my_salon_team_permissions(
    payload: SalonTeamPermissions,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_salon_team_permissions(db, _current_user_row(db, current_user), payload)


# ---------------------------------------------------
# Notification Preferences (booking reminders)
# ---------------------------------------------------

@users.get(
    "/me/notification-preferences",
    response_model=NotificationPreferenceResponse,
)
async def get_my_notification_preferences(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return get_notification_preferences_(db, current_user.user_id)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )


@users.patch(
    "/me/notification-preferences",
    response_model=NotificationPreferenceResponse,
)
async def update_my_notification_preferences(
    payload: NotificationPreferenceUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return update_notification_preferences_(db, current_user.user_id, payload)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )


@users.get("/{user_id}/profile", response_model=CustomerProfileResponse)
async def get_user_profile(
    user_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return get_customer_profile_(user_id, db, viewer_user_id=current_user.user_id)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": str(e)})

#                       END
# ---------------------------------------------------





# ---------------------------------------------------
# Service  EndPoint
# ---------------------------------------------------



# ++++++++++++++++++++++@GET+++++++++++++++++++++++++

# Header infomration
@users.get('/services/header')
async def get_service_header():
    return {
        'Salon Information header'
    }
    
# Settings
@users.get('/services/settings')
async def get_service_settings():
    return {
        'Service Settings'
    }
    
# Menu
@users.get('services/menu')
async def get_service_menu():
    return {
        'Return the menu of the service'
    }
    

# ++++++++++++++++++++++@POST++++++++++++++++++++++++


#                       END
# ---------------------------------------------------



# ---------------------------------------------------
# Admin EndPoint
# ---------------------------------------------------



# ++++++++++++++++++++++@GET+++++++++++++++++++++++++
# ++++++++++++++++++++++@POST++++++++++++++++++++++++

#                       END
# ---------------------------------------------------



# ---------------------------------------------------
# ShareHolders EndPoint
# ---------------------------------------------------



# ++++++++++++++++++++++@GET+++++++++++++++++++++++++
# ++++++++++++++++++++++@POST++++++++++++++++++++++++

#                       END
# ---------------------------------------------------


# ---------------------------------------------------
# UserTagging Endpoints
# ---------------------------------------------------



# ++++++++++++++++++++++@GET+++++++++++++++++++++++++

@users.get("/tags/search/")
async def get_user_tags(
    query: str = "",
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    
    user_id = current_user.user_id
    
    try:
        return await search_user(query, user_id, db, limit=limit, offset=offset)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": f"An unexpected error occured: {e}"})
    
        
@users.get("/tags/recent") 
async def get_recent_user_tags():
    # Best implemented in font-end with local storage/cache
    # pass
    return [
        {
            "id": "12d5690b-3c1b-46fc-9664-1b106df1f984",
            "username": "nicolo",
            "name": "Nicolo",
            "profilePicture": "http://192.168.43.160:8000/assets/images/user_profile_picture/service/1de443c7b220438cb28bfd71e14eebeb.png",
        },
        {
            "id": "142bd2f1-42f9-4527-afa5-eca024709644",
            "username": "Nicolo_xcnj4a",
            "name": "Nicoloo",
            "profilePicture": "http://192.168.43.160:8000/assets/images/user_profile_picture/service/1de443c7b220438cb28bfd71e14eebeb.png",
        },
        {
            "id": "af956e0d-9b52-4cea-9944-0f340038f62d",
            "username": "nick_n_nbiqec",
            "name": "Nick",
            "profilePicture": "http://192.168.43.160:8000/assets/images/user_profile_picture/service/1de443c7b220438cb28bfd71e14eebeb.png",
        },
    ]
    
@users.get("/tags/recommended")
async def get_recommended_user_tags(
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    
    user_id = current_user.user_id
    try:
        return await recommend_user(user_id, db, limit=limit, offset=offset)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": f"An unexpected error occured: {e}"})
    
    
    # return [
    #     {
    #         "id": "12d5690b-3c1b-46fc-9664-1b106df1f984",
    #         "username": "nicolo",
    #         "name": "Nicolo",
    #         "profile_picture": "http://192.168.43.160:8000/assets/images/user_profile_picture/service/1de443c7b220438cb28bfd71e14eebeb.png",
    #     },
    #     {
    #         "id": "142bd2f1-42f9-4527-afa5-eca024709644",
    #         "username": "Nicolo_xcnj4a",
    #         "name": "Nicoloo",
    #         "profilePicture": "http://192.168.43.160:8000/assets/images/user_profile_picture/service/1de443c7b220438cb28bfd71e14eebeb.png",
    #     },
    #     {
    #         "id": "af956e0d-9b52-4cea-9944-0f340038f62d",
    #         "username": "nick_n_nbiqec",
    #         "name": "Nick",
    #         "profilePicture": "http://192.168.43.160:8000/assets/images/user_profile_picture/service/1de443c7b220438cb28bfd71e14eebeb.png",
    #     },
    # ]
    
@users.get("/user_select_services", response_model=UserSelectServicesResponse)
async def get_user_select_services(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Simply call the service
        return await user_select_services_(current_user.user_id, db)

    except HTTPException as e:
        raise e # FastAPI handles HTTPExceptions automatically if you raise them
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )


# Simple in-memory rate limit for the public username-check endpoint.
# 30 requests per minute per IP is plenty for a real signup flow and makes
# bulk enumeration impractical. For multi-worker deploys, swap to Redis.
_CHECK_USERNAME_WINDOW = 60.0
_CHECK_USERNAME_MAX = 30
_check_username_hits: dict[str, deque] = {}
_check_username_lock = Lock()


def _enforce_check_username_rate(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    cutoff = now - _CHECK_USERNAME_WINDOW
    with _check_username_lock:
        hits = _check_username_hits.setdefault(ip, deque())
        while hits and hits[0] < cutoff:
            hits.popleft()
        if len(hits) >= _CHECK_USERNAME_MAX:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many username checks. Try again in a minute.",
            )
        hits.append(now)


@users.get("/check-username")
def check_username(
    username: str,
    request: Request,
    db: Session = Depends(get_db),
):
    _enforce_check_username_rate(request)

    username = username.strip().lower()
    if len(username) < 3:
        return {"available": False, "reason": "too_short"}
    if not username.replace("_", "").isalnum():
        return {"available": False, "reason": "invalid_chars"}
    exists = (
        db.query(User)
        .filter(func.lower(User.username) == username)
        .first()
    )
    return {"available": exists is None, "username": username}


# ++++++++++++++++++++++@POST++++++++++++++++++++++++

#                       END
# ---------------------------------------------------
