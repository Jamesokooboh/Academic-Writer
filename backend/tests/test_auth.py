from fastapi.testclient import TestClient

from app.main import app


def test_login_me_logout_roundtrip():
    with TestClient(app) as client:
        login = client.post(
            "/api/auth/login", json={"email": "admin@example.com", "password": "test-password"}
        )
        assert login.status_code == 200
        token = login.json()["access_token"]

        headers = {"Authorization": f"Bearer {token}"}
        me = client.get("/api/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["email"] == "admin@example.com"

        logout = client.post("/api/auth/logout", headers=headers)
        assert logout.status_code == 200


def test_login_rejects_wrong_password():
    with TestClient(app) as client:
        response = client.post(
            "/api/auth/login", json={"email": "admin@example.com", "password": "wrong"}
        )
        assert response.status_code == 401


def test_me_rejects_missing_token():
    with TestClient(app) as client:
        response = client.get("/api/auth/me")
        assert response.status_code in (401, 403)
