"""Pydantic API schemas for Admin Control endpoints."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CreateUserRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: str = Field("ADMIN", description="ADMIN or MAIN_ADMIN")


class UpdateUserRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=120)
    email: EmailStr | None = None
    role: str | None = None
    is_active: bool | None = None
    password: str | None = Field(None, min_length=8)


class PasswordResetActionRequest(BaseModel):
    action: str = Field(..., description="approve_temp, approve_link, or reject")
    temp_password: str | None = Field(None, min_length=8)


class LoginActivityResponse(BaseModel):
    id: str
    user_id: str | None = None
    email_attempted: str
    login_time: datetime
    ip_address: str | None = None
    user_agent: str | None = None
    success: bool
    failure_reason: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PasswordResetRequestResponse(BaseModel):
    id: str
    user_id: str
    user_email: str | None = None
    user_name: str | None = None
    status: str
    requested_at: datetime
    handled_by: str | None = None
    handled_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
