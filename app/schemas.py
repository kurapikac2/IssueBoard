"""Separate input and output schemas prevent hashes from entering API responses."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Status = Literal["open", "in_progress", "done"]
Priority = Literal["low", "medium", "high"]
IssueType = Literal["bug", "task"]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
ProjectName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Credentials(InputModel):
    username: Annotated[str, StringConstraints(
        strip_whitespace=True, min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_]+$"
    )]
    password: str = Field(min_length=10, max_length=128)


class UserOut(BaseModel):
    id: int
    username: str


class SessionOut(UserOut):
    csrf_token: str


class ProjectCreate(InputModel):
    name: ProjectName
    description: str = Field(default="", max_length=2000)


class ProjectOut(ProjectCreate):
    model_config = ConfigDict(extra="ignore")
    id: int
    created_at: str


class IssueCreate(InputModel):
    title: Title
    description: str = Field(default="", max_length=10000)
    type: IssueType = "task"
    priority: Priority = "medium"
    status: Status = "open"


class IssueUpdate(IssueCreate):
    """PUT replaces every editable field, so omitted optional fields get defaults."""


class IssueOut(IssueCreate):
    id: int
    project_id: int
    created_at: str
    updated_at: str


class HistoryOut(BaseModel):
    id: int
    actor: str
    old_status: Status | None
    new_status: Status
    changed_at: str


class MetricsOut(BaseModel):
    total: int
    open: int
    in_progress: int
    done: int