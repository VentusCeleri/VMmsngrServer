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


def create_joined_pair() -> tuple[dict, dict, dict]:
    user_a = register_user("max_pair")
    user_b = register_user("vika_pair")
    headers_a = auth_headers(user_a)
    headers_b = auth_headers(user_b)
    pair_response = client.post("/api/v1/pairs", headers=headers_a)
    assert pair_response.status_code == 201, pair_response.text
    pair = pair_response.json()
    join_response = client.post("/api/v1/pairs/join", headers=headers_b, json={"invite_code": pair["invite_code"]})
    assert join_response.status_code == 200, join_response.text
    return user_a, user_b, join_response.json()


def test_leave_pair_reopens_vacated_slot() -> None:
    user_a, user_b, pair = create_joined_pair()
    headers_a = auth_headers(user_a)
    headers_b = auth_headers(user_b)

    leave_response = client.post("/api/v1/pairs/leave", headers=headers_a)
    assert leave_response.status_code == 204, leave_response.text

    assert client.get("/api/v1/pairs/me", headers=headers_a).status_code == 404
    remaining_pair_response = client.get("/api/v1/pairs/me", headers=headers_b)
    assert remaining_pair_response.status_code == 200, remaining_pair_response.text
    remaining_pair = remaining_pair_response.json()
    assert remaining_pair["user_a_id"] is None
    assert remaining_pair["user_b_id"] == user_b["user"]["id"]

    user_c = register_user("max_return")
    rejoin_response = client.post(
        "/api/v1/pairs/join",
        headers=auth_headers(user_c),
        json={"invite_code": pair["invite_code"]},
    )
    assert rejoin_response.status_code == 200, rejoin_response.text
    assert rejoin_response.json()["user_a_id"] == user_c["user"]["id"]


def test_delete_pair_removes_pair_data_and_notifies_websockets() -> None:
    user_a, user_b, _ = create_joined_pair()
    headers_a = auth_headers(user_a)
    headers_b = auth_headers(user_b)

    task_response = client.post("/api/v1/tasks", headers=headers_a, json={"title": "Remove me"})
    assert task_response.status_code == 201, task_response.text
    message_response = client.post(
        "/api/v1/messages",
        headers=headers_b,
        json={"body": "This pair will be deleted", "receiver_id": user_a["user"]["id"]},
    )
    assert message_response.status_code == 201, message_response.text

    with client.websocket_connect(f"/api/v1/ws?token={user_b['access_token']}") as ws_b:
        assert ws_b.receive_json()["event"] == "connection.ready"
        delete_response = client.delete("/api/v1/pairs/me", headers=headers_a)
        assert delete_response.status_code == 204, delete_response.text

        event = ws_b.receive_json()
        while event["event"] != "pair.deleted":
            event = ws_b.receive_json()
        assert event["data"]["pair_id"] is not None

    assert client.get("/api/v1/pairs/me", headers=headers_a).status_code == 404
    assert client.get("/api/v1/pairs/me", headers=headers_b).status_code == 404
    assert client.get("/api/v1/tasks", headers=headers_a).status_code == 404
    assert client.get("/api/v1/messages", headers=headers_b).status_code == 404


def test_delete_account_leaves_pair_and_revokes_refresh_tokens() -> None:
    user_a, user_b, _ = create_joined_pair()
    headers_a = auth_headers(user_a)
    headers_b = auth_headers(user_b)

    task_response = client.post(
        "/api/v1/tasks",
        headers=headers_a,
        json={"title": "Owned by A", "assignee_id": user_b["user"]["id"]},
    )
    assert task_response.status_code == 201, task_response.text
    partner_task_response = client.post(
        "/api/v1/tasks",
        headers=headers_b,
        json={"title": "Assigned to A", "assignee_id": user_a["user"]["id"]},
    )
    assert partner_task_response.status_code == 201, partner_task_response.text

    delete_response = client.delete("/api/v1/users/me", headers=headers_a)
    assert delete_response.status_code == 204, delete_response.text

    assert client.get("/api/v1/auth/me", headers=headers_a).status_code == 401
    refresh_response = client.post("/api/v1/auth/refresh", json={"refresh_token": user_a["refresh_token"]})
    assert refresh_response.status_code == 401

    pair_response = client.get("/api/v1/pairs/me", headers=headers_b)
    assert pair_response.status_code == 200, pair_response.text
    assert pair_response.json()["user_a_id"] is None
    assert pair_response.json()["user_b_id"] == user_b["user"]["id"]

    tasks_response = client.get("/api/v1/tasks", headers=headers_b)
    assert tasks_response.status_code == 200, tasks_response.text
    tasks = tasks_response.json()
    assert all(task["owner_id"] != user_a["user"]["id"] for task in tasks)
    assert all(task["assignee_id"] != user_a["user"]["id"] for task in tasks)
