from datetime import timedelta
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from pydantic_schemas.auth.jwt_token import TokenData
from service.auth.JWT.JWT_token import create_access_token, verify_refresh_token, verify_token

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
async def refresh_token(request: Request):
    refresh_token = request.headers.get("Authorization")
    
    if refresh_token is None or not refresh_token.startswith("Bearer "):
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Refresh token not found",
        )
        
    refersh_token = refresh_token.split(" ")[1] # Remove Bearer from token
    
    credentials_exception = HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail = "Could not validate refresh token",
        headers = {"WWW-Authenticate": "Bearer"}, 
    )
    
    # Verify the refresh token
    token_data = verify_refresh_token(refresh_token, credentials_exception)
    
    # If the refresh token is valid, issue new access token
    new_access_token = create_access_token(
        data = {"sub": token_data.user_id},
        expire_delta = timedelta(minutes = 60),  # Set the expiration time for the new access token    
    )
    
    return {
        "access_token": new_access_token, 
        "token_type": "bearer",
    }
    
