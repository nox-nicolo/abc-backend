from typing import Optional
from fastapi import File, UploadFile
from pydantic import BaseModel, HttpUrl, Field


class UserProfileResponse(BaseModel):
    username: str
    pictureUrl: HttpUrl | None
    


class UsernameCheckRequest(BaseModel):
    username: str = Field(..., min_length=6, max_length=20, pattern=r'^[a-zA-Z0-9_]+$')
    
    

class SetupProfileRequest(BaseModel):
    username: str 
    
