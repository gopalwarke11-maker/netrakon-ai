"""FastAPI security dependencies for user authentication and role-based access control."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token, UserRole
from app.db.models import UserRecord
from app.db.session import get_db

security_bearer = HTTPBearer(auto_error=False)


def extract_token(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_bearer)],
) -> str | None:
    """Extract token from Authorization header or HttpOnly cookie."""
    if credentials and credentials.credentials:
        return credentials.credentials
    cookie_token = request.cookies.get("netrakon_auth")
    if cookie_token:
        return cookie_token
    return None


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[str | None, Depends(extract_token)],
) -> UserRecord:
    """Retrieve currently authenticated user from validated JWT token."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = str(payload["sub"])
    user = db.scalar(select(UserRecord).where(UserRecord.id == user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_active_user(
    current_user: Annotated[UserRecord, Depends(get_current_user)],
) -> UserRecord:
    """Ensure the authenticated user account is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been disabled. Please contact the Main Administrator.",
        )
    return current_user


def require_main_admin(
    current_user: Annotated[UserRecord, Depends(require_active_user)],
) -> UserRecord:
    """Ensure the authenticated user possesses the MAIN_ADMIN role."""
    if current_user.role != UserRole.MAIN_ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Main Administrator privilege required",
        )
    return current_user
