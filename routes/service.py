
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from core.database import get_db
from pydantic_schemas.auth.jwt_token import TokenData
from pydantic_schemas.services.event import EventCard
from pydantic_schemas.services.service import MajorServiceResponse, MinorServiceResponse
from service.auth.JWT.oauth2 import get_current_user
from service.services.event import get_featured_events
from service.services.services import _get_major, _get_minor, _minor_upload, all_services, major_upload

service = APIRouter(
    tags = ["Services"],
    prefix = "/services"
)



# get all services
@service.get("/")
async def get_all(db: Session = Depends(get_db), current_user: TokenData = Depends(get_current_user)):
    """
    Get all services
    """
    
    try: 
        return await all_services(db= db)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": f"An unexpected error occured: {e}"})
    



@service.post("/major")
async def upload_major(
    major: str = Form(), 
    description: str = Form(None), 
    img_upload: UploadFile = File(...), 
    db: Session = Depends(get_db), 
    current_user: TokenData = Depends(get_current_user)
):
    """
    Upload major service
    """
    
    try:
        return await major_upload(
            major = major, 
            details = description, 
            img_upload = img_upload, 
            db = db
        )
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": f"An unexpected error occured: {e}"})
    


# get major service 
@service.get("/major", response_model=list[MajorServiceResponse])
async def get_major(db: Session = Depends(get_db), current_user: TokenData = Depends(get_current_user)):
    
    """
    Get major service
    
    """
    try:
        result = await _get_major(db = db)
        return result
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content=['detail', e.detail])
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=['detail', f'An unexpected error occured: {e}'])
    pass



# get minor service 
@service.get("/minor", response_model=list[MinorServiceResponse])
async def get_minor(db: Session = Depends(get_db), current_user: TokenData = Depends(get_current_user)):
    """
    Get minor service
    """
    
    try:
        return await _get_minor(db = db)
    except HTTPException as e:
        return JSONResponse(
                status_code=e.status_code, 
                content={"detail": e.detail}
            )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            content={"detail": f"An unexpected error occured: {e}"}
        )
        

@service.get("", response_model=list[EventCard])
def fetch_events(
    limit: int = Query(10, le=20),
    db: Session = Depends(get_db),
):

    results = get_featured_events(db, limit)

    return [
        EventCard(
            event_id=sub.id,
            title=sub.name,
            description=sub.description,
            price=price.price_min if price else None,
            currency=price.currency if price else None,
            salon_id=salon.id if salon else None,
            salon_name=salon.title if salon else None,
            salon_logo=(
                salon.user.profile_picture.image_url
                if salon and salon.user and salon.user.profile_picture
                else None
            ),
        )
        for sub, price, salon in results
    ]


# Upload Minor services
@service.post("/minor")
async def upload_minor(
    service: str = Form(),
    name: str = Form(),
    description: str = Form(None),
    file_name: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user) 
):
    try:
        return await _minor_upload(
            parent_service = service,
            name = name,
            description = description,
            db = db,
            file_name = file_name
        )
        
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code, 
            content={"detail": e.detail}
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            content={"detail": f"An unexpected error occured: {e}"}
        )



