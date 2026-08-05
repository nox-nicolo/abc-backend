"""Provides the Auth API route module for the backend application."""

from fastapi import Depends, HTTPException, APIRouter, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy import or_

from core.database import get_db
from core.enumeration import AccountAccessStatus
from core.hash_pass import Hash
from core.rate_limit import rate_limit
from models.auth.refresh_token import RefreshToken
from models.auth.user import User
from pydantic_schemas.auth.jwt_token import TokenData
from pydantic_schemas.auth.me import MeResponseSchema
from pydantic_schemas.auth.password_reset import ForgotPasswordRequest, ResetPasswordRequest
from pydantic_schemas.auth.user_create import UserCreate
from sqlalchemy.orm import Session

from pydantic_schemas.auth.user_verification import UserVerification
from service.auth import create_user, login_user, password_reset, verify_user
from service.auth.JWT.oauth2 import get_current_user, refresh_token
from service.auth.me import me_
from service.account.audit import record_audit_event


class LogoutRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)


class AccountStatusRequest(BaseModel):
    password: str = Field(..., min_length=1)

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
@auth.post('/login', dependencies=[Depends(rate_limit(bucket="auth:login", limit=8, window_seconds=60))])
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


@auth.post('/forgot-password', dependencies=[Depends(rate_limit(bucket="auth:forgot-password", limit=3, window_seconds=300))])
async def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    try:
        return await password_reset.request_password_reset(str(body.email), db)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": f"An unexpected error occured: {e}"})


@auth.post('/reset-password', dependencies=[Depends(rate_limit(bucket="auth:reset-password", limit=5, window_seconds=300))])
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    try:
        return password_reset.reset_password(
            token=body.token,
            new_password=body.new_password,
            db=db,
        )
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": f"An unexpected error occured: {e}"})
    
    
# verify route
@auth.post('/verify', dependencies=[Depends(rate_limit(bucket="auth:verify", limit=10, window_seconds=60))])
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
@auth.post('/code', dependencies=[Depends(rate_limit(bucket="auth:code", limit=3, window_seconds=300))])
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
async def refresh_token_(request: Request, db: Session = Depends(get_db)):
    try:
        result = await refresh_token(request, db)
        if result:
            return result
        else:
            return result
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": f"An unexpected error occured: {e}"})


@auth.post('/logout', status_code=status.HTTP_200_OK)
def logout(body: LogoutRequest, db: Session = Depends(get_db)):
    db_token = db.query(RefreshToken).filter(
        RefreshToken.token == body.refresh_token,
        RefreshToken.revoked == False,
    ).first()
    if db_token:
        db_token.revoked = True
        db.commit()
    return {"detail": "Logged out"} 


@auth.post('/change-password', status_code=status.HTTP_200_OK)
def change_password(
    body: ChangePasswordRequest,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == current_user.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not Hash.verify(body.current_password, user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    user.password = Hash.hashing(body.new_password)
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked == False,
    ).update({"revoked": True}, synchronize_session=False)
    db.commit()
    record_audit_event(
        db,
        user_id=user.id,
        event_type="password_changed",
        title="Password changed",
        description="Account password was changed and active sessions were revoked.",
        metadata={"sessions_revoked": True},
    )
    return {"detail": "Password changed. Please sign in again."}


@auth.get('/login-history', status_code=status.HTTP_200_OK)
def login_history(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tokens = (
        db.query(RefreshToken)
        .filter(RefreshToken.user_id == current_user.user_id)
        .order_by(RefreshToken.created_at.desc())
        .limit(20)
        .all()
    )
    return {
        "items": [
            {
                "id": token.id,
                "created_at": token.created_at,
                "revoked": token.revoked,
            }
            for token in tokens
        ]
    }


@auth.post('/account/deactivate', status_code=status.HTTP_200_OK)
def deactivate_account(
    body: AccountStatusRequest,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == current_user.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not Hash.verify(body.password, user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password is incorrect")

    user.account_access = AccountAccessStatus.SUSPENDED
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked == False,
    ).update({"revoked": True}, synchronize_session=False)
    db.commit()
    return {"detail": "Account deactivated"}


@auth.delete('/account', status_code=status.HTTP_200_OK)
def delete_account(
    body: AccountStatusRequest,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == current_user.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not Hash.verify(body.password, user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password is incorrect")

    user.account_access = AccountAccessStatus.DELETED
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked == False,
    ).update({"revoked": True}, synchronize_session=False)
    db.commit()
    return {"detail": "Account deleted"}
    
    
    
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
