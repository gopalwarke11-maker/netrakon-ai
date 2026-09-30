"""FastAPI routes for password reset request, Main Admin request queue, and reset token confirmation."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_main_admin
from app.core.security import (
    generate_reset_token,
    hash_password,
    hash_reset_token,
    normalize_email,
    PasswordResetStatus,
)
from app.db.models import PasswordResetRequestRecord, UserRecord
from app.db.session import get_db
from app.models.admin_control import (
    PasswordResetActionRequest,
    PasswordResetRequestResponse,
)
from app.services.email import send_password_reset_email

router = APIRouter(tags=["password-reset"])


class PasswordResetRequestPayload(BaseModel):
    email: EmailStr


class ConfirmPasswordResetPayload(BaseModel):
    token: str = Field(..., min_length=10)
    new_password: str = Field(..., min_length=8)


@router.post("/auth/password-reset/request", summary="Submit password assistance request to Main Admin")
def request_password_reset(
    payload: PasswordResetRequestPayload,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    normalized_email = normalize_email(payload.email)
    user = db.scalar(select(UserRecord).where(UserRecord.email == normalized_email))

    # Record request if user exists, avoiding duplicate pending spam
    if user and user.is_active:
        existing_pending = db.scalar(
            select(PasswordResetRequestRecord).where(
                PasswordResetRequestRecord.user_id == user.id,
                PasswordResetRequestRecord.status == PasswordResetStatus.PENDING.value,
            )
        )
        if not existing_pending:
            req_record = PasswordResetRequestRecord(
                id=f"req_{uuid.uuid4().hex[:16]}",
                user_id=user.id,
                status=PasswordResetStatus.PENDING.value,
                requested_at=datetime.now(timezone.utc),
            )
            db.add(req_record)
            db.commit()

    return {"message": "Your password reset request has been sent to the Main Administrator."}


@router.get("/admin/password-requests", response_model=list[PasswordResetRequestResponse], summary="List password reset requests")
def list_password_requests(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserRecord, Depends(require_main_admin)],
) -> list[PasswordResetRequestResponse]:
    requests = db.scalars(
        select(PasswordResetRequestRecord).order_by(PasswordResetRequestRecord.requested_at.desc())
    ).all()

    result: list[PasswordResetRequestResponse] = []
    for req in requests:
        res = PasswordResetRequestResponse.model_validate(req)
        if req.user:
            res.user_email = req.user.email
            res.user_name = req.user.name
        result.append(res)
    return result


@router.post("/admin/password-requests/{request_id}/action", summary="Main Admin action on password reset request")
def handle_password_request(
    request_id: str,
    payload: PasswordResetActionRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserRecord, Depends(require_main_admin)],
) -> dict[str, str]:
    req_record = db.scalar(
        select(PasswordResetRequestRecord).where(PasswordResetRequestRecord.id == request_id)
    )
    if not req_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Password reset request not found")

    user = req_record.user
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user account no longer exists")

    now = datetime.now(timezone.utc)

    if payload.action == "approve_temp":
        if not payload.temp_password or len(payload.temp_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Temporary password must be at least 8 characters long",
            )
        user.password_hash = hash_password(payload.temp_password)
        user.updated_at = now
        req_record.status = PasswordResetStatus.COMPLETED.value
        req_record.handled_by = current_user.id
        req_record.handled_at = now
        db.commit()
        return {"message": f"Temporary password successfully updated for {user.name}."}

    elif payload.action in {"approve_link", "approve"}:
        raw_token = generate_reset_token()
        token_hash = hash_reset_token(raw_token)
        expires_at = now + timedelta(minutes=15)

        req_record.status = PasswordResetStatus.APPROVED.value
        req_record.token_hash = token_hash
        req_record.expires_at = expires_at
        req_record.handled_by = current_user.id
        req_record.handled_at = now
        db.commit()

        # Dispatch email to the requesting user's registered email address
        send_password_reset_email(to_email=user.email, to_name=user.name, reset_token=raw_token)

        reset_url = f"/reset-password?token={raw_token}&req={req_record.id}"
        return {
            "message": f"Password reset link generated and sent to {user.email}.",
            "reset_token": raw_token,
            "reset_url": reset_url,
        }

    elif payload.action == "reject":
        req_record.status = PasswordResetStatus.REJECTED.value
        req_record.handled_by = current_user.id
        req_record.handled_at = now
        db.commit()
        return {"message": "Password reset request rejected."}

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Use 'approve_temp', 'approve_link', 'approve', or 'reject'",
        )


@router.post("/auth/password-reset/confirm", summary="Confirm password reset using token")
def confirm_password_reset(
    payload: ConfirmPasswordResetPayload,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    incoming_hash = hash_reset_token(payload.token)
    now = datetime.now(timezone.utc)

    req_record = db.scalar(
        select(PasswordResetRequestRecord).where(
            PasswordResetRequestRecord.token_hash == incoming_hash,
            PasswordResetRequestRecord.status == PasswordResetStatus.APPROVED.value,
        )
    )

    if not req_record or not req_record.user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset link.",
        )

    if req_record.expires_at and req_record.expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset link.",
        )

    user = req_record.user
    user.password_hash = hash_password(payload.new_password)
    user.updated_at = now

    req_record.status = PasswordResetStatus.COMPLETED.value
    db.commit()

    return {"message": "Password updated successfully. You may now log in with your new password."}
