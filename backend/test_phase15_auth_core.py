"""Unit tests for Stage 4 backend authentication core."""

from datetime import timedelta
import pytest
from fastapi import HTTPException, status

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    normalize_email,
    UserRole,
    verify_password,
)
from app.api.dependencies import require_active_user, require_main_admin
from app.db.models import UserRecord


def test_password_hashing_and_verification():
    plain = "SuperSecurePassword123!"
    hashed = hash_password(plain)
    assert hashed != plain
    assert hashed.startswith("$argon2id$")
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_email_normalization():
    assert normalize_email("  ADMIN@NetraKon.AI  ") == "admin@netrakon.ai"


def test_jwt_token_generation_and_decoding():
    token = create_access_token(user_id="usr_test123", email="admin@netrakon.ai", role="ADMIN")
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "usr_test123"
    assert payload["email"] == "admin@netrakon.ai"
    assert payload["role"] == "ADMIN"


def test_jwt_token_expiration():
    expired_token = create_access_token(
        user_id="usr_test123",
        email="admin@netrakon.ai",
        role="ADMIN",
        expires_delta=timedelta(seconds=-10),
    )
    payload = decode_access_token(expired_token)
    assert payload is None


def test_invalid_jwt_token():
    assert decode_access_token("invalid.token.structure") is None


def test_require_active_user_check():
    active_user = UserRecord(id="1", name="Active", email="a@a.com", role="ADMIN", is_active=True)
    inactive_user = UserRecord(id="2", name="Inactive", email="b@b.com", role="ADMIN", is_active=False)

    assert require_active_user(active_user) == active_user

    with pytest.raises(HTTPException) as exc_info:
        require_active_user(inactive_user)
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


def test_require_main_admin_check():
    admin_user = UserRecord(id="1", name="Admin", email="a@a.com", role=UserRole.ADMIN.value, is_active=True)
    main_admin_user = UserRecord(id="2", name="MainAdmin", email="b@b.com", role=UserRole.MAIN_ADMIN.value, is_active=True)

    assert require_main_admin(main_admin_user) == main_admin_user

    with pytest.raises(HTTPException) as exc_info:
        require_main_admin(admin_user)
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
