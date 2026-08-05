"""Provides the Trust request and response schema module for profile workflows."""

from pydantic import BaseModel


class TrustIndicator(BaseModel):
    key: str
    label: str
    is_met: bool
    status: str
    detail: str


class TrustStatusResponse(BaseModel):
    role: str
    verified_email: bool
    verified_phone: bool
    verified_salon_owner: bool
    business_document_uploaded: bool
    profile_review_status: str
    safety_badge: bool
    indicators: list[TrustIndicator]


class BusinessDocumentUploadResponse(BaseModel):
    id: str
    review_status: str
    detail: str
