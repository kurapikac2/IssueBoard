"""Ownership and transaction boundaries live here, not in frontend controls."""
import sqlite3
from datetime import datetime, timezone

from app.schemas import IssueCreate, IssueUpdate, ProjectCreate
from app.services.errors import ServiceError


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def project(db: sqlite3.Connection, project_id: int, owner_id: int) -> dict:
    row = db.execute(
        "SELECT * FROM projects WHERE id = ? AND owner_id = ?", (project_id, owner_id)
    ).fetchone()
    if row is None:
        # Same response for missing and foreign resources avoids leaking existence.
        raise ServiceError(404, "Проект не найден.")
    return dict(row)


def projects(db: sqlite3.Connection, owner_id: int) -> list[dict]:
    return [dict(row) for row in db.execute(
        "SELECT * FROM projects WHERE owner_id = ? ORDER BY id DESC", (owner_id,)
    )]


def create_project(db: sqlite3.Connection, owner_id: int, data: ProjectCreate) -> dict:
    with db:
        cursor = db.execute(
            "INSERT INTO projects(owner_id, name, description, created_at) VALUES (?, ?, ?, ?)",
            (owner_id, data.name, data.description, timestamp()),
        )
    return project(db, cursor.lastrowid, owner_id)


def issue(db: sqlite3.Connection, project_id: int, issue_id: int, owner_id: int) -> dict:
    project(db, project_id, owner_id)
    row = db.execute(
        "SELECT * FROM issues WHERE id = ? AND project_id = ?", (issue_id, project_id)
    ).fetchone()
    if row is None:
        raise ServiceError(404, "Issue не найден.")
    return dict(row)


def list_issues(db, project_id, owner_id, q="", status=None, priority=None, sort="desc"):
    project(db, project_id, owner_id)
    # Python casefold supports Cyrillic; SQLite's built-in LOWER is ASCII-only.
    query = "SELECT * FROM issues WHERE project_id = ?"
    params = [project_id]
    if status:
        query += " AND status = ?"
        params.append(status)
    if priority:
        query += " AND priority = ?"
        params.append(priority)
    # SQL syntax uses a fixed allowlist, never a raw query parameter.
    ordering = "ASC" if sort == "asc" else "DESC"
    rows = db.execute(query + f" ORDER BY updated_at {ordering}, id {ordering}", params)
    return [dict(row) for row in rows if q.casefold() in row["title"].casefold()]


def create_issue(db: sqlite3.Connection, project_id: int, owner_id: int, data: IssueCreate):
    project(db, project_id, owner_id)
    now = timestamp()
    with db:
        cursor = db.execute(
            """INSERT INTO issues(project_id,title,description,type,priority,status,created_at,updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (project_id, data.title, data.description, data.type, data.priority, data.status, now, now),
        )
        db.execute(
            """INSERT INTO status_history(issue_id,actor_id,old_status,new_status,changed_at)
               VALUES (?, ?, NULL, ?, ?)""",
            (cursor.lastrowid, owner_id, data.status, now),
        )
    return issue(db, project_id, cursor.lastrowid, owner_id)


def update_issue(db: sqlite3.Connection, project_id: int, issue_id: int,
                 owner_id: int, data: IssueUpdate):
    # Serialize read + change + audit entry, so concurrent updates keep correct old_status.
    with db:
        db.execute("BEGIN IMMEDIATE")
        previous = issue(db, project_id, issue_id, owner_id)
        now = timestamp()
        db.execute(
            """UPDATE issues SET title=?,description=?,type=?,priority=?,status=?,updated_at=?
               WHERE id=? AND project_id=?""",
            (data.title, data.description, data.type, data.priority, data.status,
             now, issue_id, project_id),
        )
        if previous["status"] != data.status:
            db.execute(
                """INSERT INTO status_history(issue_id,actor_id,old_status,new_status,changed_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (issue_id, owner_id, previous["status"], data.status, now),
            )
    return issue(db, project_id, issue_id, owner_id)


def delete_issue(db: sqlite3.Connection, project_id: int, issue_id: int, owner_id: int):
    issue(db, project_id, issue_id, owner_id)
    with db:
        db.execute("DELETE FROM issues WHERE id=? AND project_id=?", (issue_id, project_id))


def history(db: sqlite3.Connection, project_id: int, issue_id: int, owner_id: int):
    issue(db, project_id, issue_id, owner_id)
    return [dict(row) for row in db.execute(
        """SELECT h.id,u.username AS actor,h.old_status,h.new_status,h.changed_at
           FROM status_history h JOIN users u ON u.id=h.actor_id
           WHERE h.issue_id=? ORDER BY h.id ASC""", (issue_id,)
    )]


def metrics(db: sqlite3.Connection, project_id: int, owner_id: int):
    project(db, project_id, owner_id)
    result = {"total": 0, "open": 0, "in_progress": 0, "done": 0}
    for row in db.execute(
        "SELECT status,COUNT(*) AS count FROM issues WHERE project_id=? GROUP BY status",
        (project_id,),
    ):
        result[row["status"]] = row["count"]
        result["total"] += row["count"]
    return result