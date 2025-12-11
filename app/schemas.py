from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class OrganizationBase(BaseModel):
    organization_name: str = Field(..., examples=["acme"])


class OrganizationCreateRequest(OrganizationBase):
    email: EmailStr
    password: str = Field(..., min_length=6)


class OrganizationUpdateRequest(OrganizationBase):
    new_organization_name: Optional[str] = Field(None, examples=["acme-new"])
    new_email: Optional[EmailStr] = None
    new_password: Optional[str] = Field(None, min_length=6)


class OrganizationResponse(OrganizationBase):
    collection_name: str
    admin_email: EmailStr
    created_at: datetime


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

