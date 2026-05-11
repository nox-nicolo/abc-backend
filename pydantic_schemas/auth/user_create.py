from pydantic import BaseModel, EmailStr, field_validator


class UserBase(BaseModel):  # Common fields
    name: str
    email: EmailStr
    phone: str
    password: str
    role: str = "customer"

    @field_validator("role")
    @classmethod
    def validate_public_signup_role(cls, value: str) -> str:
        role = (value or "customer").strip().lower()
        if role in {"customer", "user", ""}:
            return "customer"
        if role in {"service", "salon", "salon_owner", "owner"}:
            return "service"
        raise ValueError("Public signup only supports customer or salon owner accounts")


class UserCreate(UserBase):
    pass


class UserComplete(UserBase):
    username: str
