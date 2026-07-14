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
            "display_name": "Макс" if prefix.startswith("max") else "Вика",
            "password": "password123",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_headers(auth: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {auth['access_token']}"}


def test_register_requires_unique_case_insensitive_username() -> None:
    suffix = int(time.time() * 1000)
    first = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"unique.{suffix}@example.com",
            "username": f"family_{suffix}",
            "display_name": "Family",
            "password": "password123",
        },
    )
    assert first.status_code == 201, first.text

    duplicate = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"other.{suffix}@example.com",
            "username": f"FAMILY_{suffix}",
            "display_name": "Other",
            "password": "password123",
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "username_already_exists"


def test_invalid_username_uses_error_envelope() -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"invalid.{int(time.time() * 1000)}@example.com",
            "username": "bad username",
            "display_name": "Bad",
            "password": "password123",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_partner_profile_presence_and_profile_update() -> None:
    user_a = register_user("max_contract")
    user_b = register_user("vika_contract")
    headers_a = auth_headers(user_a)
    headers_b = auth_headers(user_b)

    pair_response = client.post("/api/v1/pairs", headers=headers_a)
    assert pair_response.status_code == 201, pair_response.text
    pair = pair_response.json()

    join_response = client.post("/api/v1/pairs/join", headers=headers_b, json={"invite_code": pair["invite_code"]})
    assert join_response.status_code == 200, join_response.text

    partner_response = client.get("/api/v1/pairs/me/partner", headers=headers_a)
    assert partner_response.status_code == 200, partner_response.text
    partner = partner_response.json()
    assert partner["user"]["display_name"] == "Вика"
    assert partner["presence"]["is_online"] is False

    update_response = client.patch(
        "/api/v1/users/me",
        headers=headers_b,
        json={"username": f"vcnew{str(int(time.time() * 1000))[-10:]}", "display_name": "Вика Новая"},
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["display_name"] == "Вика Новая"


def test_websocket_presence_events() -> None:
    user_a = register_user("max_ws")
    user_b = register_user("vika_ws")
    headers_a = auth_headers(user_a)
    headers_b = auth_headers(user_b)

    pair = client.post("/api/v1/pairs", headers=headers_a).json()
    assert client.post("/api/v1/pairs/join", headers=headers_b, json={"invite_code": pair["invite_code"]}).status_code == 200

    with client.websocket_connect(f"/api/v1/ws?token={user_a['access_token']}") as ws_a:
        assert ws_a.receive_json()["event"] == "connection.ready"
        with client.websocket_connect(f"/api/v1/ws?token={user_b['access_token']}") as ws_b:
            assert ws_b.receive_json()["event"] == "connection.ready"
            online_event = ws_a.receive_json()
            while online_event["event"] != "presence.updated" or online_event["data"]["user_id"] != user_b["user"]["id"]:
                online_event = ws_a.receive_json()
            assert online_event["data"]["is_online"] is True

        offline_event = ws_a.receive_json()
        while offline_event["event"] != "presence.updated" or offline_event["data"]["user_id"] != user_b["user"]["id"]:
            offline_event = ws_a.receive_json()
        assert offline_event["data"]["is_online"] is False
        assert offline_event["data"]["last_seen_at"] is not None


def test_ready_endpoint() -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
