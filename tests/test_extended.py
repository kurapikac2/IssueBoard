import sqlite3
import time

from fastapi.testclient import TestClient

from app.main import create_app
from helpers import make_issue, register_and_login


def test_combined_filters_unicode_search_and_sort(signed_in, project):
    root = f"/api/projects/{project['id']}/issues"
    first = make_issue(signed_in, project, title="Ошибка SQLite", status="open")
    second = make_issue(signed_in, project, title="ОШИБКА API", priority="low", status="done")
    third = make_issue(signed_in, project, title="Документация", priority="low")
    assert [i["id"] for i in signed_in.get(root, params={"q": "ошибка"}).json()] == [second["id"], first["id"]]
    assert [i["id"] for i in signed_in.get(root, params={
        "q": "оШиБкА", "priority": "high", "status": "open"
    }).json()] == [first["id"]]
    assert [i["id"] for i in signed_in.get(root, params={"sort": "asc"}).json()] == [
        first["id"], second["id"], third["id"]
    ]
    assert signed_in.get(root, params={"q": "' OR 1=1 --"}).json() == []
    assert signed_in.get(root, params={"q": "%"}).json() == []
    assert signed_in.get(root, params={"status": "bad"}).status_code == 422
    assert signed_in.get(root, params={"sort": "updated_at; DROP TABLE issues"}).status_code == 422
    assert len(signed_in.get(root).json()) == 3
    body = {"title": first["title"], "type": "bug", "priority": "high", "status": "in_progress"}
    signed_in.put(root + f"/{first['id']}", json=body)
    assert signed_in.get(root).json()[0]["id"] == first["id"]


def test_history_records_actor_old_new_time_and_noop(signed_in, project):
    issue = make_issue(signed_in, project)
    path = f"/api/projects/{project['id']}/issues/{issue['id']}"
    body = {"title": "Renamed", "type": "bug", "priority": "high", "status": "in_progress"}
    assert signed_in.put(path, json=body).status_code == 200
    assert signed_in.put(path, json=body).status_code == 200
    body["status"] = "done"
    assert signed_in.put(path, json=body).status_code == 200
    history = signed_in.get(path + "/history").json()
    assert [(h["old_status"], h["new_status"]) for h in history] == [
        (None, "open"), ("open", "in_progress"), ("in_progress", "done")
    ]
    assert all(h["actor"] == "student_one" for h in history)
    assert all(h["changed_at"].endswith("+00:00") for h in history)
    assert history[0]["changed_at"] <= history[1]["changed_at"] <= history[2]["changed_at"]


def test_metrics_ignore_list_filters_and_follow_deletion(signed_in, project):
    root = f"/api/projects/{project['id']}"
    assert signed_in.get(root + "/metrics").json() == {"total": 0, "open": 0, "in_progress": 0, "done": 0}
    make_issue(signed_in, project, status="open")
    make_issue(signed_in, project, status="in_progress")
    done = make_issue(signed_in, project, status="done")
    assert len(signed_in.get(root + "/issues?status=done").json()) == 1
    assert signed_in.get(root + "/metrics").json() == {"total": 3, "open": 1, "in_progress": 1, "done": 1}
    signed_in.delete(root + f"/issues/{done['id']}")
    assert signed_in.get(root + "/metrics").json() == {"total": 2, "open": 1, "in_progress": 1, "done": 0}


def test_history_transaction_rolls_back_if_audit_fails(signed_in, project, settings):
    issue = make_issue(signed_in, project)
    with sqlite3.connect(settings.database) as db:
        db.execute("""CREATE TRIGGER fail_audit BEFORE INSERT ON status_history
                      BEGIN SELECT RAISE(ABORT, 'test audit failure'); END""")
    # A real database failure, not a mock: issue change must roll back as well.
    with TestClient(create_app(settings), raise_server_exceptions=False) as browser:
        browser.cookies.update(signed_in.cookies)
        browser.headers["X-CSRF-Token"] = signed_in.headers["X-CSRF-Token"]
        response = browser.put(f"/api/projects/{project['id']}/issues/{issue['id']}",
                               json={"title": "Changed", "status": "done"})
        assert response.status_code == 500
    assert signed_in.get(f"/api/projects/{project['id']}/issues/{issue['id']}").json() == issue


def test_cross_project_issue_mismatch(signed_in, project):
    issue = make_issue(signed_in, project)
    second = signed_in.post("/api/projects", json={"name": "Other owned project"}).json()
    path = f"/api/projects/{second['id']}/issues/{issue['id']}"
    assert signed_in.get(path).status_code == 404
    assert signed_in.put(path, json={"title": "Wrong project"}).status_code == 404
    assert signed_in.delete(path).status_code == 404
    assert signed_in.get(path + "/history").status_code == 404


def test_expired_session(signed_in, settings):
    with sqlite3.connect(settings.database) as db:
        db.execute("UPDATE sessions SET expires_at=?", (int(time.time()) - 1,))
    assert signed_in.get("/api/projects").status_code == 401


def test_rate_limit(client):
    for _ in range(20):
        assert client.post("/api/auth/login", json={
            "username": "missing_user", "password": "test-password-123"
        }).status_code == 401
    response = client.post("/api/auth/login", json={
        "username": "missing_user", "password": "test-password-123"
    })
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "600"


def test_origin_and_security_headers(signed_in):
    response = signed_in.post("/api/projects", json={"name": "Blocked"},
                              headers={"Origin": "https://evil.example"})
    assert response.status_code == 403
    response = signed_in.get("/api/projects")
    assert response.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["x-content-type-options"] == "nosniff"


def test_static_pages_and_openapi(client):
    response = client.get("/")
    assert response.status_code == 200
    assert 'lang="ru"' in response.text
    assert client.get("/static/styles.css").status_code == 200
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_delete_cascades_history(signed_in, project, settings):
    issue = make_issue(signed_in, project)
    signed_in.delete(f"/api/projects/{project['id']}/issues/{issue['id']}")
    with sqlite3.connect(settings.database) as db:
        assert db.execute("SELECT COUNT(*) FROM status_history").fetchone()[0] == 0


def test_secure_cookie_configuration(settings):
    from dataclasses import replace
    secure = replace(settings, cookie_secure=True)
    with TestClient(create_app(secure), base_url="https://testserver") as browser:
        register_and_login(browser)
        response = browser.post("/api/auth/login", json={
            "username": "student_one", "password": "test-password-123"
        })
        assert "secure" in response.headers["set-cookie"].lower()
def test_non_ascii_csrf_returns_forbidden(signed_in):
    response = signed_in.post("/api/projects", json={"name": "Blocked"},
                              headers={"X-CSRF-Token": b"\xe9"})
    assert response.status_code == 403


def test_session_rotation_and_hashed_storage(signed_in, settings):
    previous = signed_in.cookies.get("issueboard_session")
    response = signed_in.post("/api/auth/login", json={
        "username": "student_one", "password": "test-password-123"
    })
    assert response.status_code == 200
    current = signed_in.cookies.get("issueboard_session")
    assert previous != current
    with sqlite3.connect(settings.database) as db:
        tokens = [row[0] for row in db.execute("SELECT token_hash FROM sessions")]
    assert len(tokens) == 1
    assert current not in tokens and previous not in tokens
    with TestClient(create_app(settings)) as stale:
        stale.cookies.set("issueboard_session", previous)
        assert stale.get("/api/auth/session").status_code == 401
