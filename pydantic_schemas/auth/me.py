from pydantic import BaseModel
from typing import Optional


class MeResponseSchema(BaseModel):
    id: str 
    username: str 
    phone: str 
    role: str 
    profile_picture: Optional[str] = None
