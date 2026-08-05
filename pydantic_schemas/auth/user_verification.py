"""Provides the User Verification request and response schema module for auth workflows."""

from pydantic import BaseModel

class UserVerification(BaseModel):
    code: str