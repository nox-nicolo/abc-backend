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
from service.customer.following import get_my_following
from service.customer.profile import get_customer_profile_, update_customer_profile_
from service.search.users import recommend_user, search_user
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
        return get_customer_profile_(current_user.user_id, db)
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
        return update_customer_profile_(current_user.user_id, data, db)
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
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_mutes(db=db, user_id=current_user.user_id, target_type=target_type)


@users.post("/me/mutes/{target_type}/{target_id}", response_model=MuteResponse, status_code=200)
def mute_target_route(
    target_type: MuteTargetType,
    target_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return mute_target(
        db=db,
        user_id=current_user.user_id,
        target_type=target_type,
        target_id=target_id,
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
        return get_customer_profile_(user_id, db)
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
