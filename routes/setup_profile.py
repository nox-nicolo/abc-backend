from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from core.database import get_db
from pydantic_schemas.auth.jwt_token import TokenData
from pydantic_schemas.services.service import ServiceListRequest
from pydantic_schemas.set_account.set_account import UserProfileResponse, UsernameCheckRequest
from service.auth.JWT.oauth2 import get_current_user
from service.set_account.set_profile import selected_, check_username, get_account, upload_account_

setup = APIRouter(
    prefix='/setup',
    tags=['Setup Profile'],
) # so this route will be protected from email verification 

@setup.get('/setup_account', response_model = UserProfileResponse)
async def setup_account(db: Session = Depends(get_db), current_user: TokenData = Depends(get_current_user)):
    user_id = current_user.user_id
    try:
        return await get_account(user_id, db)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": f"An unexpected error occured: {e}"})
    

@setup.post('/check_username')
async def try_username(request: UsernameCheckRequest, db: Session = Depends(get_db), current_user: TokenData = Depends(get_current_user)):
    user_id = current_user.user_id
    
    print(user_id)
    
    try:
        return await check_username(request, user_id,  db)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": f"An unexpected error occured: {e}"})
    

@setup.patch('/upload_account')
async def upload_account(data: str = Form(...), image_name: UploadFile = File(None), db: Session = Depends(get_db), current_user: TokenData = Depends(get_current_user)):
    
    user_id = current_user.user_id
    
    try:
        return await upload_account_(user_id = user_id, data = data, image_name = image_name, db = db)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    
    
# write service to the user database
@setup.post('/services_selected')
async def user_select(list_selected: ServiceListRequest, db: Session = Depends(get_db), current_user: TokenData = Depends(get_current_user)):
    """
    Write service to the user database
    """
    user = current_user.user_id
    try:
        return await selected_(list_selected, user_id = user, db = db)
    except HTTPException as e:
        return JSONResponse(status_code = e.status_code, content={"detail": e.detail})
    except Exception as e:
        return JSONResponse(status_code = status.HTTP_500_INTERNAL_SERVER_ERROR, content = {"detail": f"An unexpected error occored: {e}"})
   