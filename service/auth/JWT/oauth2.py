from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

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
async def refresh_token(request: Request):
    refresh_token = request.headers.get("Authorization")
    
    if refresh_token is None or not refresh_token.startswith("Bearer "):
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Refresh token not found",
        )
        
    token_str = refresh_token.split(" ")[1]  # Remove Bearer from token

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Verify the refresh token
    token_data = verify_refresh_token(token_str, credentials_exception)

    # Issue new access token
    new_access_token = create_access_token(data={"sub": token_data.user_id})

    # Issue new refresh token (rotation — old one is replaced)
    new_refresh_token = create_refresh_token(data={"sub": token_data.user_id})

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }
    
