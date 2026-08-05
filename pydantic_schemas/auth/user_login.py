"""Provides the User Login request and response schema module for auth workflows."""

from pydantic import BaseModel


class UserLogin(BaseModel):
    
    username: str
    password: str

