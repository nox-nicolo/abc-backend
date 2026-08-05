"""Provides the Send Code request and response schema module for auth workflows."""

from pydantic import BaseModel, EmailStr


class EmailSchema(BaseModel):
    email: list[EmailStr]
