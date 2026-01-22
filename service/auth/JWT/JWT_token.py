
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt

from pydantic_schemas.auth.jwt_token import TokenData

# To get the key llke that 
# run openssl rand -hex 32

SECRET_KEY = "6d812761b157200f2e112e2438627e2cb6fc43791826b1f25c06056266cb18a4"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10  # 60 minutes
REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30  # 30 days



# create access token
def create_access_token(data: dict, expire_delta: Optional[timedelta] = None):
    
    to_encode = data.copy()
    
    if expire_delta:
        expire = datetime.now() + expire_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes = ACCESS_TOKEN_EXPIRE_MINUTES)
        
    to_encode.update({'exp': expire})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm = ALGORITHM)
    
    return encoded_jwt

# Verifiy jwt access token 
def verify_token(token: str, exception):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms = [ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise exception
        return TokenData(user_id=user_id)  # Must return a proper model or dict
    except JWTError:
        raise exception
    
    

# Create refresh access token
def create_refresh_token(data: dict):
    to_encode = data.copy() 
    
    expire = datetime.utcnow() + timedelta(days = REFRESH_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({'exp': expire}) 
    
    refresh_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm = ALGORITHM)
    
    return refresh_jwt 


# Create verify refresh token 
def verify_refresh_token(token: str, exception):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms = [ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None: 
            raise exception 
        return TokenData(user_id = user_id)  # Must return a proper model or dict
    except JWTError:
        raise exception 