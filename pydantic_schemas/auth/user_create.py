from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator, model_validator


class UserBase(BaseModel):  # Common fields
    name: str
    username: Optional[str] = None
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
        if role == "admin":
            return "admin"
        raise ValueError("Signup only supports customer, salon owner, or admin accounts")

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        username = value.strip().lower()
        if not username:
            return None

        if any(char.isspace() for char in username):
            raise ValueError("Username cannot contain spaces")

        return username

    @model_validator(mode="after")
    def validate_admin_username(self):
        if self.role == "admin" and not self.username:
            raise ValueError("Username is required for admin accounts")
        return self


class UserCreate(UserBase):
    pass


class UserComplete(UserBase):
    username: str
