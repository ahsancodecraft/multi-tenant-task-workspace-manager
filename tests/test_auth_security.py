from datetime import datetime, timedelta, timezone
import jwt
from app.core.config import settings


def test_register_user_success_omits_password_hash(client):
    # Arrange
    payload = {"email": "Alice@Example.com", "password": "StrongPassword123!"}

    # Act
    response = client.post("/api/auth/register", json=payload)

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "alice@example.com"
    assert data["role"] == "user"
    assert "password_hash" not in data
    assert "password" not in data


def test_register_duplicate_email_returns_409(client):
    # Arrange
    payload = {"email": "duplicate@example.com", "password": "StrongPassword123!"}
    client.post("/api/auth/register", json=payload)

    # Act
    response = client.post("/api/auth/register", json=payload)

    # Assert
    assert response.status_code == 409


def test_register_weak_short_password_returns_422(client):
    # Arrange
    payload = {"email": "weak@example.com", "password": "short123"}

    # Act
    response = client.post("/api/auth/register", json=payload)

    # Assert
    assert response.status_code == 422


def test_login_valid_credentials_returns_jwt(client):
    # Arrange
    client.post(
        "/api/auth/register",
        json={"email": "login@example.com", "password": "StrongPassword123!"},
    )

    # Act
    response = client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "StrongPassword123!"},
    )

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 20


def test_login_wrong_password_returns_401(client):
    # Arrange
    client.post(
        "/api/auth/register",
        json={"email": "user@example.com", "password": "StrongPassword123!"},
    )

    # Act
    response = client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "WrongPassword999!"},
    )

    # Assert
    assert response.status_code == 401


def test_protected_route_without_token_returns_401(client):
    # Act
    response = client.get("/api/tasks")

    # Assert
    assert response.status_code == 401


def test_protected_route_with_expired_jwt_returns_401(client):
    # Arrange: Create a token that expired 5 minutes ago
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    expired_token = jwt.encode(
        {"sub": "1", "role": "user", "iat": past, "exp": past},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    # Act
    response = client.get(
        "/api/tasks",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    # Assert
    assert response.status_code == 401
    
from app.db.models import UserModel
from tests.conftest import TestingSessionLocal


def test_standard_user_cannot_access_admin_routes_returns_403(client, auth_headers_factory):
    # Arrange
    user_headers = auth_headers_factory("normal_user@example.com")

    # Act & Assert
    overview_res = client.get("/api/admin/overview", headers=user_headers)
    delete_res = client.delete("/api/admin/tasks/1", headers=user_headers)

    assert overview_res.status_code == 403
    assert delete_res.status_code == 403


def test_admin_user_can_access_overview_and_remove_any_task(client, auth_headers_factory):
    # Arrange: Standard user creates a workspace & task
    alice_headers = auth_headers_factory("tenant_alice@example.com")
    ws_id = client.post("/api/workspaces", json={"name": "Alice Team"}, headers=alice_headers).json()["id"]
    task_id = client.post(
        "/api/tasks",
        json={"workspace_id": ws_id, "title": "Policy violating task", "priority": "URGENT"},
        headers=alice_headers,
    ).json()["id"]

    # Register an admin account and elevate role in isolated test DB
    client.post(
        "/api/auth/register",
        json={"email": "superadmin@example.com", "password": "StrongPassword123!"},
    )
    db = TestingSessionLocal()
    try:
        admin_row = db.query(UserModel).filter(UserModel.email == "superadmin@example.com").first()
        admin_row.role = "admin"
        db.commit()
    finally:
        db.close()

    admin_token = client.post(
        "/api/auth/login",
        json={"email": "superadmin@example.com", "password": "StrongPassword123!"},
    ).json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Act 1: Admin inspects system-wide overview
    overview_res = client.get("/api/admin/overview", headers=admin_headers)
    assert overview_res.status_code == 200
    overview = overview_res.json()
    assert overview["total_users"] == 2
    assert overview["total_workspaces"] == 1
    assert overview["total_tasks"] == 1
    assert overview["urgent_tasks"] == 1

    # Act 2: Admin removes policy-violating task
    del_res = client.delete(f"/api/admin/tasks/{task_id}", headers=admin_headers)
    assert del_res.status_code == 204
    assert client.get(f"/api/tasks/{task_id}", headers=alice_headers).status_code == 404