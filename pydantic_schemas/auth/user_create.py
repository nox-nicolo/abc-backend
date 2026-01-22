from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):  # Common fields
    name: str
    email: EmailStr
    phone: str
    password: str
    role: str


class UserCreate(UserBase):
    pass


class UserComplete(UserBase):
    username: str  
    

