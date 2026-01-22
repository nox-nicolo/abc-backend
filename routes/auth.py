
from fastapi import Depends, HTTPException, APIRouter, Request, status 
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_

from core.database import get_db
from pydantic_schemas.auth.jwt_token import TokenData
from pydantic_schemas.auth.jwt_token import TokenData
from pydantic_schemas.auth.me import MeResponseSchema
from pydantic_schemas.auth.user_create import UserCreate
from sqlalchemy.orm import Session

from pydantic_schemas.auth.user_verification import UserVerification
from service.auth import create_user, login_user, verify_user
from service.auth.JWT.oauth2 import get_current_user, refresh_token
from service.auth.me import me_

auth = APIRouter(
    prefix='/auth',
    tags=['Authenications']
    )  # instance of the fastapi for input route in different file ( so is like a fastapi in the main file )

# signup user route
@auth.post('/signup', status_code = 201,)
async def signup_user(user: UserCreate, db: Session = Depends(get_db)): # db is a type Session from sqlachemy.orm and its a depence get_db
    """_summary_

    Args:
        user (UserCreate): _description_. User created
        db (Session, optional): _description_. Defaults to Depends(get_db).

    Returns:
        _type_: _description_. 201 CREATED and send verification code to provided email
    """
    
    try:
        db_user = await create_user.create_user(user, db)
        return db_user
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": f"An unexpected error occured: {e}"})
   

# login user route
@auth.post('/login')
def login(user: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
        Login user
    """
    try: 
        user = login_user.login_user(user, db)
        if user:
            return user
        else:
            return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": "Invalid credentials"})
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    
    
# verify route
@auth.post('/verify')
def verify_endpoint(verification: UserVerification, db: Session = Depends(get_db)):
    
    try:
        result = verify_user.verify_user(verification.code, db)
        if result:
            return result
        else: 
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": "Invalid verification token or"})
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    
    
# send code route to user via mail
@auth.post('/code')
async def send_code(verifcation: UserVerification, db: Session = Depends(get_db)):
    
    try:
        result = await verify_user.code_expires(verifcation.code, db=db)
        if result:
            return {"message": "New erification code sent successfully, Go to your mail"}
        else:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": "Something went wrong"})
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


@auth.post('/refersh')
async def refresh_token_(request: Request):
    try:
        result = await refresh_token(request) 
        if result: 
            return result
        else:
            return result 
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:  
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": f"An unexpected error occured: {e}"}) 
    
    
    
@auth.get('/me', response_model= MeResponseSchema, status_code=status.HTTP_200_OK)
async def me(current_user: TokenData = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user.user_id
    
    try: 
        result = await me_(user_id = user_id, db = db)
        return result
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail}) 
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": f"An unexpected error occured: {e}"})