"""Integration tests for Stages 7-11: Admin Control Panel, Password Reset Requests, and Audit Logging."""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import hash_password, UserRole
from app.db.models import UserRecord
from app.db.session import SessionLocal
from app.main import app


def get_auth_headers(email: str, password: str) -> dict[str, str]:
    test_client = TestClient(app)
    res = test_client.post("/api/auth/login", json={"email": email, "password": password})
    if res.status_code != 200:
        raise ValueError(f"Login failed for {email}: {res.text}")
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def setup_admin_data():
    with SessionLocal() as db:
        m_admin = db.scalar(select(UserRecord).where(UserRecord.email == "main_suite@netrakon.ai"))
        if not m_admin:
            db.add(
                UserRecord(
                    id="usr_main_suite",
                    name="Main Suite Admin",
                    email="main_suite@netrakon.ai",
                    password_hash=hash_password("MainSuite123!"),
                    role=UserRole.MAIN_ADMIN.value,
                    is_active=True,
                )
            )
        else:
            m_admin.password_hash = hash_password("MainSuite123!")
            m_admin.is_active = True

        n_admin = db.scalar(select(UserRecord).where(UserRecord.email == "normal_suite@netrakon.ai"))
        if not n_admin:
            db.add(
                UserRecord(
                    id="usr_normal_suite",
                    name="Normal Suite Admin",
                    email="normal_suite@netrakon.ai",
                    password_hash=hash_password("NormalSuite123!"),
                    role=UserRole.ADMIN.value,
                    is_active=True,
                )
            )
        else:
            n_admin.password_hash = hash_password("NormalSuite123!")
            n_admin.is_active = True

        db.commit()


def test_admin_control_access_control():
    test_client = TestClient(app)
    admin_headers = get_auth_headers("normal_suite@netrakon.ai", "NormalSuite123!")
    main_headers = get_auth_headers("main_suite@netrakon.ai", "MainSuite123!")

    # ADMIN -> 403 Forbidden
    res_admin = test_client.get("/api/admin/users", headers=admin_headers)
    assert res_admin.status_code == 403

    # MAIN_ADMIN -> 200 OK
    res_main = test_client.get("/api/admin/users", headers=main_headers)
    assert res_main.status_code == 200
    assert isinstance(res_main.json(), list)


def test_main_admin_user_creation_and_duplication():
    test_client = TestClient(app)
    main_headers = get_auth_headers("main_suite@netrakon.ai", "MainSuite123!")
    unique_email = f"op_{uuid.uuid4().hex[:6]}@netrakon.ai"

    # Create new ADMIN
    create_res = test_client.post(
        "/api/admin/users",
        headers=main_headers,
        json={
            "name": "New Operator",
            "email": unique_email,
            "password": "OperatorPass123!",
            "role": "ADMIN",
        },
    )
    assert create_res.status_code == 201
    assert create_res.json()["email"] == unique_email.lower()

    # Duplicate email attempt -> 400
    dup_res = test_client.post(
        "/api/admin/users",
        headers=main_headers,
        json={
            "name": "Dup Operator",
            "email": unique_email.upper(),
            "password": "OperatorPass123!",
            "role": "ADMIN",
        },
    )
    assert dup_res.status_code == 400


def test_main_admin_safety_constraints():
    test_client = TestClient(app)
    main_headers = get_auth_headers("main_suite@netrakon.ai", "MainSuite123!")

    with SessionLocal() as db:
        m_user = db.scalar(select(UserRecord).where(UserRecord.email == "main_suite@netrakon.ai"))
        main_id = m_user.id

    # 1. MAIN_ADMIN cannot deactivate self
    deact_self = test_client.patch(
        f"/api/admin/users/{main_id}",
        headers=main_headers,
        json={"is_active": False},
    )
    assert deact_self.status_code == 400
    assert "cannot deactivate your own" in deact_self.json()["detail"].lower()

    # 2. MAIN_ADMIN cannot delete self
    del_self = test_client.delete(f"/api/admin/users/{main_id}", headers=main_headers)
    assert del_self.status_code == 400
    assert "cannot delete your own" in del_self.json()["detail"].lower()


def test_password_reset_request_and_action_flow():
    test_client = TestClient(app)

    # 1. Submit reset request
    req_res = test_client.post(
        "/api/auth/password-reset/request",
        json={"email": "normal_suite@netrakon.ai"},
    )
    assert req_res.status_code == 200
    assert "sent" in req_res.json()["message"].lower()

    main_headers = get_auth_headers("main_suite@netrakon.ai", "MainSuite123!")

    # 2. Main Admin lists requests
    list_res = test_client.get("/api/admin/password-requests", headers=main_headers)
    assert list_res.status_code == 200
    requests = list_res.json()
    assert len(requests) > 0
    req_id = requests[0]["id"]

    # 3. Main Admin sets temporary password
    act_res = test_client.post(
        f"/api/admin/password-requests/{req_id}/action",
        headers=main_headers,
        json={"action": "approve_temp", "temp_password": "NewTempPass123!"},
    )
    assert act_res.status_code == 200

    # 4. Verify login with temporary password
    temp_login = test_client.post(
        "/api/auth/login",
        json={"email": "normal_suite@netrakon.ai", "password": "NewTempPass123!"},
    )
    assert temp_login.status_code == 200


def test_audit_activity_logging_endpoint():
    test_client = TestClient(app)
    main_headers = get_auth_headers("main_suite@netrakon.ai", "MainSuite123!")
    act_res = test_client.get("/api/admin/activity", headers=main_headers)
    assert act_res.status_code == 200
    logs = act_res.json()
    assert isinstance(logs, list)
    assert len(logs) > 0


def test_password_reset_link_email_delivery_and_confirm_flow():
    test_client = TestClient(app)

    # 1. User submits reset request for normal_suite@netrakon.ai
    req_res = test_client.post(
        "/api/auth/password-reset/request",
        json={"email": "normal_suite@netrakon.ai"},
    )
    assert req_res.status_code == 200

    main_headers = get_auth_headers("main_suite@netrakon.ai", "MainSuite123!")

    # 2. Main Admin lists requests and approves with approve_link
    list_res = test_client.get("/api/admin/password-requests", headers=main_headers)
    assert list_res.status_code == 200
    requests = list_res.json()
    req_id = requests[0]["id"]

    act_res = test_client.post(
        f"/api/admin/password-requests/{req_id}/action",
        headers=main_headers,
        json={"action": "approve_link"},
    )
    assert act_res.status_code == 200
    data = act_res.json()
    raw_token = data["reset_token"]
    assert len(raw_token) >= 32

    # 3. Verify DB stores SHA-256 hash, NOT raw token
    with SessionLocal() as db:
        from app.db.models import PasswordResetRequestRecord
        from app.core.security import hash_reset_token
        req_db = db.scalar(select(PasswordResetRequestRecord).where(PasswordResetRequestRecord.id == req_id))
        assert req_db.token_hash == hash_reset_token(raw_token)
        assert req_db.token_hash != raw_token
        assert req_db.user.email == "normal_suite@netrakon.ai"

    # 4. User confirms password reset with new password
    confirm_res = test_client.post(
        "/api/auth/password-reset/confirm",
        json={"token": raw_token, "new_password": "NewLinkPass123!"},
    )
    assert confirm_res.status_code == 200

    # 5. Verify single-use: reusing same token fails
    reconfirm_res = test_client.post(
        "/api/auth/password-reset/confirm",
        json={"token": raw_token, "new_password": "NewLinkPass123!"},
    )
    assert reconfirm_res.status_code == 400

    # 6. Verify old password no longer works
    old_login = test_client.post(
        "/api/auth/login",
        json={"email": "normal_suite@netrakon.ai", "password": "MainSuite123!"},
    )
    assert old_login.status_code == 401

    # 7. Verify new password works
    new_login = test_client.post(
        "/api/auth/login",
        json={"email": "normal_suite@netrakon.ai", "password": "NewLinkPass123!"},
    )
    assert new_login.status_code == 200


def test_password_reset_token_expiration():
    from datetime import datetime, timedelta, timezone
    from app.db.models import PasswordResetRequestRecord
    from app.core.security import generate_reset_token, hash_reset_token

    test_client = TestClient(app)
    raw_token = generate_reset_token()
    token_hash = hash_reset_token(raw_token)

    with SessionLocal() as db:
        u = db.scalar(select(UserRecord).where(UserRecord.email == "normal_suite@netrakon.ai"))
        expired_req = PasswordResetRequestRecord(
            id=f"req_exp_{uuid.uuid4().hex[:8]}",
            user_id=u.id,
            status="APPROVED",
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        )
        db.add(expired_req)
        db.commit()

    confirm_res = test_client.post(
        "/api/auth/password-reset/confirm",
        json={"token": raw_token, "new_password": "ExpiredPass123!"},
    )
    assert confirm_res.status_code == 400
    assert "expired" in confirm_res.json()["detail"].lower()


def test_unauthenticated_and_admin_direct_api_denials():
    test_client = TestClient(app)
    admin_headers = get_auth_headers("normal_suite@netrakon.ai", "NormalSuite123!")

    # Unauthenticated GET -> 401
    unauth_res = test_client.get("/api/admin/users")
    assert unauth_res.status_code == 401

    # ADMIN GET -> 403
    admin_get = test_client.get("/api/admin/users", headers=admin_headers)
    assert admin_get.status_code == 403

    # ADMIN POST -> 403
    admin_post = test_client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={"name": "Hacker", "email": "hack@netrakon.ai", "password": "HackPassword123!", "role": "MAIN_ADMIN"},
    )
    assert admin_post.status_code == 403

