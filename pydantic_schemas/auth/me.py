from pydantic import BaseModel


class MeResponseSchema(BaseModel):
    id: str 
    username: str 
    phone: str 
    role: str 
    profile_picture: str