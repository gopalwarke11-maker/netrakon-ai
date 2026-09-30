"""Integration tests for Stage 5 authentication API endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import hash_password, UserRole
from app.db.models import LoginActivityRecord, UserRecord
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_users():
    """Ensure clean test users exist in database before running tests."""
    with SessionLocal() as db:
        # 1. Active Admin
        existing_admin = db.scalar(select(UserRecord).where(UserRecord.email == "test_admin@netrakon.ai"))
        if not existing_admin:
            db.add(
                UserRecord(
                    id="usr_test_admin",
                    name="Test Admin",
                    email="test_admin@netrakon.ai",
                    password_hash=hash_password("AdminPass123!"),
                    role=UserRole.ADMIN.value,
                    is_active=True,
                )
            )

        # 2. Active Main Admin
        existing_main = db.scalar(select(UserRecord).where(UserRecord.email == "test_main@netrakon.ai"))
        if not existing_main:
            db.add(
                UserRecord(
                    id="usr_test_main",
                    name="Test Main Admin",
                    email="test_main@netrakon.ai",
                    password_hash=hash_password("MainPass123!"),
                    role=UserRole.MAIN_ADMIN.value,
                    is_active=True,
                )
            )

        # 3. Disabled Admin
        existing_disabled = db.scalar(select(UserRecord).where(UserRecord.email == "disabled_admin@netrakon.ai"))
        if not existing_disabled:
            db.add(
                UserRecord(
                    id="usr_test_disabled",
                    name="Disabled Admin",
                    email="disabled_admin@netrakon.ai",
                    password_hash=hash_password("DisabledPass123!"),
                    role=UserRole.ADMIN.value,
                    is_active=False,
                )
            )

        db.commit()


def test_login_success_admin():
    response = client.post(
        "/api/auth/login",
        json={"email": "TEST_ADMIN@netrakon.ai", "password": "AdminPass123!", "remember_me": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "test_admin@netrakon.ai"
    assert data["user"]["role"] == "ADMIN"
    assert "netrakon_auth" in response.cookies


def test_login_success_main_admin():
    response = client.post(
        "/api/auth/login",
        json={"email": "test_main@netrakon.ai", "password": "MainPass123!", "remember_me": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["role"] == "MAIN_ADMIN"
    assert "netrakon_auth" in response.cookies


def test_login_invalid_password():
    response = client.post(
        "/api/auth/login",
        json={"email": "test_admin@netrakon.ai", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"

    with SessionLocal() as db:
        logs = db.scalars(
            select(LoginActivityRecord)
            .where(LoginActivityRecord.email_attempted == "test_admin@netrakon.ai")
            .order_by(LoginActivityRecord.login_time.desc())
        ).all()
        assert len(logs) > 0
        assert logs[0].success is False


def test_login_unknown_email():
    response = client.post(
        "/api/auth/login",
        json={"email": "nonexistent@netrakon.ai", "password": "AnyPassword!"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_disabled_account():
    response = client.post(
        "/api/auth/login",
        json={"email": "disabled_admin@netrakon.ai", "password": "DisabledPass123!"},
    )
    assert response.status_code == 403
    assert "disabled" in response.json()["detail"].lower()


def test_get_me_authenticated():
    test_client = TestClient(app)
    login_res = test_client.post(
        "/api/auth/login",
        json={"email": "test_admin@netrakon.ai", "password": "AdminPass123!"},
    )
    token = login_res.json()["access_token"]

    res = test_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["email"] == "test_admin@netrakon.ai"


def test_get_me_unauthenticated():
    test_client = TestClient(app)
    res = test_client.get("/api/auth/me")
    assert res.status_code == 401


def test_logout():
    test_client = TestClient(app)
    res = test_client.post("/api/auth/logout")
    assert res.status_code == 200
    assert res.json()["message"] == "Logged out successfully"
