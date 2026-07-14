import time

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def register_user(prefix: str) -> dict:
    suffix = int(time.time() * 1000)
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"{prefix}.{suffix}@example.com",
            "username": f"{prefix}_{suffix}",
            "display_name": prefix.title(),
            "password": "password123",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_headers(auth: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {auth['access_token']}"}


def test_device_token_lifecycle() -> None:
    user = register_user("push_device")
    headers = auth_headers(user)
    token_a = "a" * 64
    token_b = "b" * 64

    register_response = client.post(
        "/api/v1/devices/register",
        headers=headers,
        json={"device_token": token_a, "platform": "ios"},
    )
    assert register_response.status_code == 201, register_response.text
    assert register_response.json()["device_token"] == token_a
    assert register_response.json()["active"] is True

    update_response = client.patch(
        "/api/v1/devices/token",
        headers=headers,
        json={"device_token": token_a, "new_device_token": token_b, "platform": "ios"},
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["device_token"] == token_b

    delete_response = client.request(
        "DELETE",
        "/api/v1/devices/current",
        headers=headers,
        json={"device_token": token_b},
    )
    assert delete_response.status_code == 204, delete_response.text


def test_push_endpoints_require_auth() -> None:
    response = client.post("/api/v1/devices/register", json={"device_token": "c" * 64, "platform": "ios"})
    assert response.status_code == 401
