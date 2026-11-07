import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from helpers import register_and_login


@pytest.fixture
def settings(tmp_path):
    return Settings(database=tmp_path / "test.sqlite3")


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as client:
        yield client


@pytest.fixture
def signed_in(client):
    register_and_login(client)
    return client


@pytest.fixture
def project(signed_in):
    response = signed_in.post("/api/projects", json={"name": "Учебный проект"})
    assert response.status_code == 201
    return response.json()
