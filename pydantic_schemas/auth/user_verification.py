from pydantic import BaseModel

class UserVerification(BaseModel):
    code: str