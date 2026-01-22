from datetime import timedelta
from fastapi import Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload
from core.database import get_db
from core.enumeration import AccountAccessStatus, Status,    ImageURL
from core.hash_pass import Hash
from models.auth.user import User
from pydantic_schemas.auth.user_login import UserLogin
from service.auth.JWT.JWT_token import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token, create_refresh_token

# Base URL (adjust to your server IP/domain)
BASE_URL = ImageURL.PROFILE_URL


def login_user(user: UserLogin, db: Session = Depends(get_db)):
    """

        Logs in a user and returns their information if credentials are valid. 
        
        Args: 
            user (UserLogin): Pydantic model containing user login data. 
            db (Session): Database session object
            
        Raise:
            HTTPException: status.HTTP_404_NOT_FOUND if user credential are incorenct
            
        Returns: 
            User: User object if login is successful, None otherwise.
    """
    
    # Check if user exists by username or email 
    existing_user = db.query(User)\
        .options(joinedload(User.profile_picture))\
        .filter(
            or_(
                User.email == user.username,
                User.username == user.username
            )
        )\
        .first()
    
    # check if user exists
    if not existing_user:
        raise HTTPException(
            status_code= status.HTTP_404_NOT_FOUND, 
            detail="User doesn't exist"
        )
    
    # Check if password are matching
    passwd_is_valid = Hash.verify(user.password, existing_user.password)
        # encode to change to bytes the data
    
    if not passwd_is_valid:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED, 
            detail = "Incorrect password"
        )
        
    # if user is not verified not able to login period
    if not existing_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Account is not verified"
        )
        
    # Account Access Status:
    no_access = [AccountAccessStatus.BANNED, AccountAccessStatus.DELETED, AccountAccessStatus.LOCKED, AccountAccessStatus.PENDING] 
    
    if existing_user.account_access in no_access:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Account is not active"
        )
        
    # if user found generate JWT and return it..
    
    access_token_expires = timedelta(minutes = ACCESS_TOKEN_EXPIRE_MINUTES)
    
    access_token = create_access_token(
        data = {
            "sub": str(existing_user.id)
        }, 
        expire_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data = {"sub": str(existing_user.id)}
    )

    return {
        "user_id": existing_user.id, 
        "access_token": access_token, 
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
    