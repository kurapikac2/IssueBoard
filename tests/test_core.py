import sqlite3
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from helpers import register_and_login, make_issue


def test_registration_hash_and_duplicate(client, settings):
    body = {"username": "Student", "password": "test-password-123"}
    response = client.post("/api/auth/register", json=body)
    assert response.status_code == 201
    assert set(response.json()) == {"id", "username"}
    assert response.json()["username"] == "student"
    assert client.post("/api/auth/register", json=body).status_code == 409
    with sqlite3.connect(settings.database) as db:
        stored = db.execute("SELECT password_hash FROM users").fetchone()[0]
    assert stored.startswith("$argon2id$")
    assert body["password"] not in stored


def test_login_logout_revokes_session(client):
    register_and_login(client)
    assert client.get("/api/auth/session").status_code == 200
    cookie = client.cookies.get("issueboard_session")
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/session").status_code == 401
    client.cookies.set("issueboard_session", cookie)
    assert client.get("/api/auth/session").status_code == 401


def test_wrong_credentials(client):
    register_and_login(client)
    response = client.post("/api/auth/login", json={
        "username": "student_one", "password": "wrong-password-123"
    })
    assert response.status_code == 401
    assert client.post("/api/auth/login", json={
        "username": "nonexistent", "password": "wrong-password-123"
    }).json() == response.json()


@pytest.mark.parametrize("payload", [
    {"username": "a", "password": "long-password"},
    {"username": "valid_name", "password": "short"},
    {"username": "bad name", "password": "long-password"},
    {"username": "valid_name", "password": "x" * 129},
])
def test_invalid_credentials_no_secret_echo(client, payload):
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 422
    assert payload["password"] not in response.text


def test_csrf_and_content_type(signed_in):
    signed_in.headers.pop("X-CSRF-Token")
    assert signed_in.post("/api/projects", json={"name": "Blocked"}).status_code == 403
    assert signed_in.post("/api/auth/login", data={
        "username": "student_one", "password": "test-password-123"
    }).status_code == 415


def test_anonymous_access(client):
    assert client.get("/api/projects").status_code == 401
    assert client.post("/api/projects", json={"name": "No"}).status_code == 401


def test_issue_create_update_delete(signed_in, project):
    issue = make_issue(signed_in, project)
    path = f"/api/projects/{project['id']}/issues/{issue['id']}"
    assert signed_in.get(path).json()["title"] == "Ошибка входа"
    body = {"title": "Исправить вход", "type": "task", "priority": "low",
            "description": "Подробности", "status": "in_progress"}
    response = signed_in.put(path, json=body)
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"
    assert response.json()["description"] == "Подробности"
    assert response.json()["created_at"] == issue["created_at"]
    assert response.json()["updated_at"] > issue["updated_at"]
    assert signed_in.delete(path).status_code == 204
    assert signed_in.get(path).status_code == 404


def test_foreign_project_all_actions(client, project, settings):
    item = make_issue(client, project)
    with TestClient(create_app(settings)) as other:
        register_and_login(other, "other_student")
        assert other.get("/api/projects").json() == []
        root = f"/api/projects/{project['id']}"
        issue_path = f"{root}/issues/{item['id']}"
        checks = [
            other.get(root), other.get(root + "/issues"), other.get(root + "/metrics"),
            other.post(root + "/issues", json={"title": "Intrusion"}),
            other.get(issue_path), other.get(issue_path + "/history"),
            other.put(issue_path, json={"title": "Overwrite"}),
            other.delete(issue_path),
        ]
        assert [r.status_code for r in checks] == [404] * 8
    assert client.get(f"/api/projects/{project['id']}/issues/{item['id']}").json() == item


@pytest.mark.parametrize("changes", [
    {"title": "   "}, {"title": "x" * 161}, {"status": "invalid"},
    {"priority": "urgent"}, {"type": "feature"}, {"description": "x" * 10001},
    {"owner_id": 999},
])
def test_invalid_issue(signed_in, project, changes):
    response = signed_in.post(f"/api/projects/{project['id']}/issues",
                              json={"title": "Valid", **changes})
    assert response.status_code == 422


def test_cookie_security(client):
    data = {"username": "cookie_user", "password": "test-password-123"}
    client.post("/api/auth/register", json=data)
    response = client.post("/api/auth/login", json=data)
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=strict" in cookie


def test_persistence_after_restart(settings):
    with TestClient(create_app(settings)) as first:
        register_and_login(first)
        first.post("/api/projects", json={"name": "Persistent"})
    with TestClient(create_app(settings)) as second:
        response = second.post("/api/auth/login", json={
            "username": "student_one", "password": "test-password-123"
        })
        assert response.status_code == 200
        assert second.get("/api/projects").json()[0]["name"] == "Persistent"
