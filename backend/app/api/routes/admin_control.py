"""FastAPI routes for Main Admin Control user management and audit logging."""

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_main_admin
from app.core.security import hash_password, normalize_email, UserRole
from app.db.models import LoginActivityRecord, UserRecord
from app.db.session import get_db
from app.models.admin_control import (
    CreateUserRequest,
    LoginActivityResponse,
    UpdateUserRequest,
)
from app.models.auth import UserProfileResponse

router = APIRouter(prefix="/admin", tags=["admin-control"])


def count_active_main_admins(db: Session) -> int:
    """Return total number of active MAIN_ADMIN accounts."""
    return db.scalar(
        select(func.count(UserRecord.id)).where(
            UserRecord.role == UserRole.MAIN_ADMIN.value,
            UserRecord.is_active == True,
        )
    ) or 0


@router.get("/users", response_model=list[UserProfileResponse], summary="List all administrators")
def list_users(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserRecord, Depends(require_main_admin)],
) -> list[UserProfileResponse]:
    users = db.scalars(select(UserRecord).order_by(UserRecord.created_at.desc())).all()
    return [UserProfileResponse.model_validate(u) for u in users]


@router.post("/users", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED, summary="Create administrator account")
def create_user(
    payload: CreateUserRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserRecord, Depends(require_main_admin)],
) -> UserProfileResponse:
    normalized_email = normalize_email(payload.email)
    
    # Validate role
    if not UserRole.has_value(payload.role):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Allowed values: {UserRole.ADMIN.value}, {UserRole.MAIN_ADMIN.value}",
        )

    # Check email uniqueness
    existing = db.scalar(select(UserRecord).where(UserRecord.email == normalized_email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An administrator with this email address already exists.",
        )

    pw_hash = hash_password(payload.password)
    user_id = f"usr_{uuid.uuid4().hex[:16]}"
    
    new_user = UserRecord(
        id=user_id,
        name=payload.name.strip(),
        email=normalized_email,
        password_hash=pw_hash,
        role=payload.role,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return UserProfileResponse.model_validate(new_user)


@router.get("/users/{user_id}", response_model=UserProfileResponse, summary="Get administrator details")
def get_user(
    user_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserRecord, Depends(require_main_admin)],
) -> UserProfileResponse:
    user = db.scalar(select(UserRecord).where(UserRecord.id == user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Administrator not found")
    return UserProfileResponse.model_validate(user)


@router.patch("/users/{user_id}", response_model=UserProfileResponse, summary="Update administrator profile")
def update_user(
    user_id: str,
    payload: UpdateUserRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserRecord, Depends(require_main_admin)],
) -> UserProfileResponse:
    user = db.scalar(select(UserRecord).where(UserRecord.id == user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Administrator not found")

    # Safety Check 1: Prevent Main Admin from deactivating themselves
    if user.id == current_user.id and payload.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own Main Administrator account.",
        )

    # Safety Check 2: Prevent reducing active MAIN_ADMIN count to zero
    if (
        user.role == UserRole.MAIN_ADMIN.value
        and user.is_active is True
        and (payload.is_active is False or (payload.role and payload.role != UserRole.MAIN_ADMIN.value))
    ):
        active_mains = count_active_main_admins(db)
        if active_mains <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one active Main Administrator must remain in the system.",
            )

    if payload.name:
        user.name = payload.name.strip()

    if payload.email:
        normalized_email = normalize_email(payload.email)
        if normalized_email != user.email:
            existing = db.scalar(select(UserRecord).where(UserRecord.email == normalized_email))
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email address already in use by another administrator.",
                )
            user.email = normalized_email

    if payload.role:
        if not UserRole.has_value(payload.role):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role specified.")
        user.role = payload.role

    if payload.is_active is not None:
        user.is_active = payload.is_active

    if payload.password:
        user.password_hash = hash_password(payload.password)

    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    return UserProfileResponse.model_validate(user)


@router.delete("/users/{user_id}", summary="Delete administrator account")
def delete_user(
    user_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserRecord, Depends(require_main_admin)],
) -> dict[str, str]:
    user = db.scalar(select(UserRecord).where(UserRecord.id == user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Administrator not found")

    # Safety Check 1: Cannot delete self
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own Main Administrator account.",
        )

    # Safety Check 2: Cannot delete last active MAIN_ADMIN
    if user.role == UserRole.MAIN_ADMIN.value and user.is_active:
        active_mains = count_active_main_admins(db)
        if active_mains <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one active Main Administrator must remain in the system.",
            )

    db.delete(user)
    db.commit()
    return {"message": f"Administrator '{user.name}' ({user.email}) deleted successfully"}


@router.get("/activity", response_model=list[LoginActivityResponse], summary="List authentication audit logs")
def list_activity(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserRecord, Depends(require_main_admin)],
) -> list[LoginActivityResponse]:
    logs = db.scalars(select(LoginActivityRecord).order_by(LoginActivityRecord.login_time.desc()).limit(200)).all()
    return [LoginActivityResponse.model_validate(l) for l in logs]
