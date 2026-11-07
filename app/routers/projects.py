from typing import Literal

from fastapi import APIRouter, Query, Response

from app.dependencies import Db, Session
from app.schemas import (
    HistoryOut, IssueCreate, IssueOut, IssueUpdate, MetricsOut,
    Priority, ProjectCreate, ProjectOut, Status,
)
from app.services import board

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
def projects(db: Db, user: Session):
    return board.projects(db, user["id"])


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(data: ProjectCreate, db: Db, user: Session, response: Response):
    project = board.create_project(db, user["id"], data)
    response.headers["Location"] = f"/api/projects/{project['id']}"
    return project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Db, user: Session):
    return board.project(db, project_id, user["id"])


@router.get("/{project_id}/issues", response_model=list[IssueOut])
def issues(project_id: int, db: Db, user: Session,
           q: str = Query("", max_length=160), status: Status | None = None,
           priority: Priority | None = None, sort: Literal["asc", "desc"] = "desc"):
    return board.list_issues(db, project_id, user["id"], q, status, priority, sort)


@router.post("/{project_id}/issues", response_model=IssueOut, status_code=201)
def create_issue(project_id: int, data: IssueCreate, db: Db, user: Session, response: Response):
    issue = board.create_issue(db, project_id, user["id"], data)
    response.headers["Location"] = f"/api/projects/{project_id}/issues/{issue['id']}"
    return issue


@router.get("/{project_id}/issues/{issue_id}", response_model=IssueOut)
def get_issue(project_id: int, issue_id: int, db: Db, user: Session):
    return board.issue(db, project_id, issue_id, user["id"])


@router.put("/{project_id}/issues/{issue_id}", response_model=IssueOut)
def update_issue(project_id: int, issue_id: int, data: IssueUpdate, db: Db, user: Session):
    return board.update_issue(db, project_id, issue_id, user["id"], data)


@router.delete("/{project_id}/issues/{issue_id}", status_code=204)
def delete_issue(project_id: int, issue_id: int, db: Db, user: Session):
    board.delete_issue(db, project_id, issue_id, user["id"])


@router.get("/{project_id}/issues/{issue_id}/history", response_model=list[HistoryOut])
def history(project_id: int, issue_id: int, db: Db, user: Session):
    return board.history(db, project_id, issue_id, user["id"])


@router.get("/{project_id}/metrics", response_model=MetricsOut)
def metrics(project_id: int, db: Db, user: Session):
    return board.metrics(db, project_id, user["id"])