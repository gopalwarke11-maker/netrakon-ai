"""FastAPI routes for user login, user profile verification, and logout."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_active_user
from app.core.config import settings
from app.core.security import (
    create_access_token,
    normalize_email,
    verify_password,
)
from app.db.models import LoginActivityRecord, UserRecord
from app.db.session import get_db
from app.models.auth import LoginRequest, TokenResponse, UserProfileResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


def get_client_ip(request: Request) -> str | None:
    """Extract client IP address handling proxy headers."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/login", response_model=TokenResponse, summary="Authenticate admin credentials")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    normalized_email = normalize_email(payload.email)
    ip_address = get_client_ip(request)
    user_agent = request.headers.get("user-agent")

    user = db.scalar(select(UserRecord).where(UserRecord.email == normalized_email))

    # Generic authentication failure if user not found or password mismatch
    if not user or not verify_password(payload.password, user.password_hash):
        log_entry = LoginActivityRecord(
            id=f"log_{datetime.now(timezone.utc).timestamp():.6f}",
            user_id=user.id if user else None,
            email_attempted=normalized_email,
            login_time=datetime.now(timezone.utc),
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            failure_reason="Invalid credentials",
        )
        db.add(log_entry)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Account disabled failure
    if not user.is_active:
        log_entry = LoginActivityRecord(
            id=f"log_{datetime.now(timezone.utc).timestamp():.6f}",
            user_id=user.id,
            email_attempted=normalized_email,
            login_time=datetime.now(timezone.utc),
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            failure_reason="Account disabled",
        )
        db.add(log_entry)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been disabled. Please contact the Main Administrator.",
        )

    # Successful login handling
    now = datetime.now(timezone.utc)
    user.last_login = now
    
    log_entry = LoginActivityRecord(
        id=f"log_{now.timestamp():.6f}",
        user_id=user.id,
        email_attempted=normalized_email,
        login_time=now,
        ip_address=ip_address,
        user_agent=user_agent,
        success=True,
        failure_reason=None,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(user)

    # Lifetime determination based on remember_me
    if payload.remember_me:
        expires_delta = timedelta(days=7)
        cookie_max_age = 7 * 86400
    else:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
        cookie_max_age = settings.access_token_expire_minutes * 60

    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        expires_delta=expires_delta,
    )

    # Set HttpOnly security cookie
    is_prod = settings.environment.lower() in {"production", "prod"}
    response.set_cookie(
        key="netrakon_auth",
        value=access_token,
        max_age=cookie_max_age,
        httponly=True,
        samesite="lax",
        secure=is_prod,
        path="/",
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserProfileResponse.model_validate(user),
    )


@router.get("/me", response_model=UserProfileResponse, summary="Retrieve authenticated user profile")
def get_me(
    current_user: Annotated[UserRecord, Depends(require_active_user)],
) -> UserProfileResponse:
    return UserProfileResponse.model_validate(current_user)


@router.post("/logout", summary="Clear authentication session cookie")
def logout(response: Response) -> dict[str, str]:
    is_prod = settings.environment.lower() in {"production", "prod"}
    response.delete_cookie(
        key="netrakon_auth",
        path="/",
        httponly=True,
        samesite="lax",
        secure=is_prod,
    )
    return {"message": "Logged out successfully"}
