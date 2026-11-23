def test_create_workspace_and_task_success(client, auth_headers_factory):
    # Arrange
    headers = auth_headers_factory("alice@example.com")
    ws_res = client.post("/api/workspaces", json={"name": "Backend Sprint"}, headers=headers)
    assert ws_res.status_code == 201
    ws_id = ws_res.json()["id"]

    # Act
    task_res = client.post(
        "/api/tasks",
        json={
            "workspace_id": ws_id,
            "title": "Write automated tests",
            "description": "Cover CRUD and IDOR cases",
            "priority": "HIGH",
        },
        headers=headers,
    )

    # Assert
    assert task_res.status_code == 201
    task = task_res.json()
    assert task["title"] == "Write automated tests"
    assert task["priority"] == "HIGH"
    assert task["status"] == "TODO"


def test_create_task_invalid_payload_returns_422(client, auth_headers_factory):
    # Arrange
    headers = auth_headers_factory("val@example.com")
    ws_id = client.post("/api/workspaces", json={"name": "Validation WS"}, headers=headers).json()["id"]

    # Act
    res_empty_title = client.post(
        "/api/tasks",
        json={"workspace_id": ws_id, "title": "", "priority": "MEDIUM"},
        headers=headers,
    )
    res_bad_priority = client.post(
        "/api/tasks",
        json={"workspace_id": ws_id, "title": "Valid Title", "priority": "SUPER_URGENT"},
        headers=headers,
    )

    # Assert
    assert res_empty_title.status_code == 422
    assert res_bad_priority.status_code == 422


def test_list_tasks_returns_only_current_users_tasks(client, auth_headers_factory):
    # Arrange
    alice_headers = auth_headers_factory("alice@example.com")
    bob_headers = auth_headers_factory("bob@example.com")

    ws_a = client.post("/api/workspaces", json={"name": "Alice WS"}, headers=alice_headers).json()["id"]
    ws_b = client.post("/api/workspaces", json={"name": "Bob WS"}, headers=bob_headers).json()["id"]

    client.post("/api/tasks", json={"workspace_id": ws_a, "title": "Alice Secret Task"}, headers=alice_headers)
    client.post("/api/tasks", json={"workspace_id": ws_b, "title": "Bob Private Task"}, headers=bob_headers)

    # Act
    alice_tasks = client.get("/api/tasks", headers=alice_headers).json()

    # Assert
    assert len(alice_tasks) == 1
    assert alice_tasks[0]["title"] == "Alice Secret Task"


def test_filter_tasks_by_status_and_priority(client, auth_headers_factory):
    # Arrange
    headers = auth_headers_factory("filter@example.com")
    ws_id = client.post("/api/workspaces", json={"name": "Filter WS"}, headers=headers).json()["id"]
    client.post("/api/tasks", json={"workspace_id": ws_id, "title": "Low Task", "priority": "LOW"}, headers=headers)
    client.post("/api/tasks", json={"workspace_id": ws_id, "title": "Urgent Task", "priority": "URGENT"}, headers=headers)

    # Act
    res = client.get("/api/tasks?priority=URGENT&status=TODO", headers=headers)

    # Assert
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert items[0]["title"] == "Urgent Task"


def test_update_task_and_valid_state_transition(client, auth_headers_factory):
    # Arrange
    headers = auth_headers_factory("update@example.com")
    ws_id = client.post("/api/workspaces", json={"name": "Update WS"}, headers=headers).json()["id"]
    task_id = client.post("/api/tasks", json={"workspace_id": ws_id, "title": "Draft API"}, headers=headers).json()["id"]

    # Act
    res = client.patch(
        f"/api/tasks/{task_id}",
        json={"title": "Finalize API", "status": "IN_PROGRESS"},
        headers=headers,
    )

    # Assert
    assert res.status_code == 200
    assert res.json()["title"] == "Finalize API"
    assert res.json()["status"] == "IN_PROGRESS"


def test_illegal_state_transition_returns_409(client, auth_headers_factory):
    # Arrange
    headers = auth_headers_factory("conflict@example.com")
    ws_id = client.post("/api/workspaces", json={"name": "Conflict WS"}, headers=headers).json()["id"]
    task_id = client.post("/api/tasks", json={"workspace_id": ws_id, "title": "Archive Me"}, headers=headers).json()["id"]
    client.patch(f"/api/tasks/{task_id}", json={"status": "ARCHIVED"}, headers=headers)

    # Act
    res = client.patch(f"/api/tasks/{task_id}", json={"status": "IN_PROGRESS"}, headers=headers)

    # Assert
    assert res.status_code == 409


def test_delete_own_task_and_subsequent_get_returns_404(client, auth_headers_factory):
    # Arrange
    headers = auth_headers_factory("delete@example.com")
    ws_id = client.post("/api/workspaces", json={"name": "Delete WS"}, headers=headers).json()["id"]
    task_id = client.post("/api/tasks", json={"workspace_id": ws_id, "title": "Temp Task"}, headers=headers).json()["id"]

    # Act
    del_res = client.delete(f"/api/tasks/{task_id}", headers=headers)
    get_res = client.get(f"/api/tasks/{task_id}", headers=headers)

    # Assert
    assert del_res.status_code == 204
    assert get_res.status_code == 404


def test_non_existent_task_returns_404(client, auth_headers_factory):
    # Arrange
    headers = auth_headers_factory("missing@example.com")

    # Act
    res = client.get("/api/tasks/99999", headers=headers)

    # Assert
    assert res.status_code == 404


def test_cross_tenant_idor_access_denied(client, auth_headers_factory):
    # Arrange
    alice_headers = auth_headers_factory("alice_idor@example.com")
    bob_headers = auth_headers_factory("bob_idor@example.com")

    ws_a = client.post("/api/workspaces", json={"name": "Alice Vault"}, headers=alice_headers).json()["id"]
    task_a = client.post(
        "/api/tasks",
        json={"workspace_id": ws_a, "title": "Confidential Strategy"},
        headers=alice_headers,
    ).json()["id"]

    # Act & Assert
    assert client.get(f"/api/tasks/{task_a}", headers=bob_headers).status_code == 403
    assert client.patch(f"/api/tasks/{task_a}", json={"title": "Hacked"}, headers=bob_headers).status_code == 403
    assert client.delete(f"/api/tasks/{task_a}", headers=bob_headers).status_code == 403
    assert (
        client.post(
            "/api/tasks",
            json={"workspace_id": ws_a, "title": "Injected Task"},
            headers=bob_headers,
        ).status_code
        == 403
    )