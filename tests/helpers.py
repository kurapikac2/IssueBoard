def register_and_login(client, username="student_one"):
    data = {"username": username, "password": "test-password-123"}
    assert client.post("/api/auth/register", json=data).status_code == 201
    response = client.post("/api/auth/login", json=data)
    assert response.status_code == 200
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return response.json()




def make_issue(client, project, **fields):
    body = {"title": "Ошибка входа", "type": "bug", "priority": "high", **fields}
    response = client.post(f"/api/projects/{project['id']}/issues", json=body)
    assert response.status_code == 201
    return response.json()


