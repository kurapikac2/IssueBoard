"""One SQLite connection per request; SQL values always use placeholders."""
import sqlite3
from contextlib import closing
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE COLLATE NOCASE,
 password_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
 token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
 csrf_token TEXT NOT NULL, expires_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS projects (
 id INTEGER PRIMARY KEY, owner_id INTEGER NOT NULL REFERENCES users(id),
 name TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 100),
 description TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS issues (
 id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id),
 title TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 160),
 description TEXT NOT NULL DEFAULT '',
 type TEXT NOT NULL CHECK(type IN ('bug','task')),
 priority TEXT NOT NULL CHECK(priority IN ('low','medium','high')),
 status TEXT NOT NULL CHECK(status IN ('open','in_progress','done')),
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS status_history (
 id INTEGER PRIMARY KEY, issue_id INTEGER NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
 actor_id INTEGER NOT NULL REFERENCES users(id),
 old_status TEXT, new_status TEXT NOT NULL, changed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS auth_attempts (
 ip_hash TEXT NOT NULL, attempted_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_projects_owner ON projects(owner_id);
CREATE INDEX IF NOT EXISTS idx_issues_project ON issues(project_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_history_issue ON status_history(issue_id, id);
CREATE INDEX IF NOT EXISTS idx_attempts_ip_time ON auth_attempts(ip_hash, attempted_at);
"""


def connect(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path, timeout=10, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def initialize(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(path)) as db:
        db.execute("PRAGMA journal_mode = WAL")
        db.executescript(SCHEMA)
        db.commit()


def get_db(request):
    # FastAPI dependencies below wrap this generator with a typed Request.
    with closing(connect(request.app.state.settings.database)) as db:
        yield db