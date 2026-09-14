"""
Security, Authentication & Role-Based Access Control (RBAC) Test Suite.
Verifies JWT session token generation, API route protection, password hashing, and anti-theft controls.
"""
import pytest
from fastapi.testclient import TestClient
from src.app import app
from src.db.connection import get_db_manager
from src.services.auth_service import AuthService


@pytest.fixture(autouse=True)
def init_test_database():
    """Initialize in-memory or fresh DB for tests."""
    db = get_db_manager(":memory:")
    db.initialize_database(include_seed=True)
    auth_svc = AuthService(db)
    auth_svc.ensure_bootstrap_users()
    yield db


@pytest.fixture
def client():
    return TestClient(app)


def test_unauthenticated_api_access_blocked(client):
    """Ensure any unauthorized API request returns HTTP 401 Unauthorized."""
    # 1. POS Next Invoice
    r1 = client.get("/api/sales/next-invoice-no")
    assert r1.status_code == 401

    # 2. Product Master
    r2 = client.get("/api/masters/products")
    assert r2.status_code == 401

    # 3. Farmer Master
    r3 = client.get("/api/masters/customers")
    assert r3.status_code == 401

    # 4. Profit and Loss
    r4 = client.get("/api/accounting/profit-and-loss?from_date=2026-01-01&to_date=2026-12-31")
    assert r4.status_code == 401

    # 5. Inventory Stock Summary
    r5 = client.get("/api/inventory/stock-summary")
    assert r5.status_code == 401


def test_login_failure_with_wrong_password(client):
    """Ensure invalid credentials receive 401."""
    res = client.post("/api/auth/login", json={"username": "admin", "password": "wrong_password_123"})
    assert res.status_code == 401
    assert "Invalid" in res.json()["detail"] or "चुकीचा" in res.json()["detail"]


def test_login_success_and_jwt_token_issuance(client):
    """Ensure valid admin login returns JWT token and shop metadata."""
    res = client.post("/api/auth/login", json={"username": "admin", "password": "krushidhan@2026"})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "token" in data
    assert data["user"]["username"] == "admin"
    assert data["user"]["role"] == "ADMIN"
    assert "श्री कृषीधन" in data["shop"]["name"]


def test_authenticated_api_access_allowed(client):
    """Ensure endpoints are unlocked when valid token is supplied."""
    login_res = client.post("/api/auth/login", json={"username": "admin", "password": "krushidhan@2026"})
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify session profile
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["user"]["username"] == "admin"

    # Verify POS next invoice
    inv_res = client.get("/api/sales/next-invoice-no", headers=headers)
    assert inv_res.status_code == 200
    assert "next_invoice_no" in inv_res.json()

    # Verify Product Master
    prod_res = client.get("/api/masters/products", headers=headers)
    assert prod_res.status_code == 200


def test_operator_rbac_restrictions(client):
    """Ensure operator cannot access admin-only endpoints like user management."""
    import uuid
    uid = uuid.uuid4().hex[:6]
    op_user = f"op_{uid}"

    # Login as admin to create an operator
    admin_login = client.post("/api/auth/login", json={"username": "admin", "password": "krushidhan@2026"})
    admin_token = admin_login.json()["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Create new operator
    create_res = client.post(
        "/api/auth/users",
        headers=admin_headers,
        json={"username": op_user, "password": "pass1234", "full_name": "Counter Boy", "role": "OPERATOR"},
    )
    assert create_res.status_code == 200

    # Login as operator
    op_login = client.post("/api/auth/login", json={"username": op_user, "password": "pass1234"})
    assert op_login.status_code == 200
    op_token = op_login.json()["token"]
    op_headers = {"Authorization": f"Bearer {op_token}"}

    # Operator trying to access user management -> 403 Forbidden
    user_mgmt_res = client.get("/api/auth/users", headers=op_headers)
    assert user_mgmt_res.status_code == 403


    # Operator CAN access POS Next invoice
    pos_res = client.get("/api/sales/next-invoice-no", headers=op_headers)
    assert pos_res.status_code == 200


def test_change_password_flow(client):
    """Ensure user can change their own password."""
    # Login as admin
    login_res = client.post("/api/auth/login", json={"username": "admin", "password": "krushidhan@2026"})
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Change password
    change_res = client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"old_password": "krushidhan@2026", "new_password": "new_secure_pwd_2026"},
    )
    assert change_res.status_code == 200

    # Login with new password
    new_login = client.post("/api/auth/login", json={"username": "admin", "password": "new_secure_pwd_2026"})
    assert new_login.status_code == 200
