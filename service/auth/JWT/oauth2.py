from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from core.database import get_db
from models.auth.refresh_token import RefreshToken
from pydantic_schemas.auth.jwt_token import TokenData
from service.auth.JWT.JWT_token import create_access_token, create_refresh_token, verify_refresh_token, verify_token

token_auth_scheme = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(token_auth_scheme)):
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    return verify_token(token, credentials_exception)


# Refresh Token Service
async def refresh_token(request: Request, db: Session = Depends(get_db)):
    auth_header = request.headers.get("Authorization")

    if auth_header is None or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found",
        )

    token_str = auth_header.split(" ")[1]

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data = verify_refresh_token(token_str, credentials_exception)

    # Check token exists in DB and is not revoked
    db_token = db.query(RefreshToken).filter(
        RefreshToken.token == token_str,
        RefreshToken.revoked == False,
    ).first()
    if db_token is None:
        raise credentials_exception

    # Rotate: revoke old token, issue new ones
    db_token.revoked = True

    new_access_token = create_access_token(data={"sub": token_data.user_id})
    new_refresh_token = create_refresh_token(data={"sub": token_data.user_id})

    new_db_token = RefreshToken(user_id=token_data.user_id, token=new_refresh_token)
    db.add(new_db_token)
    db.commit()

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }
    
