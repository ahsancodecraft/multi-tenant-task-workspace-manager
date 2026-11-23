from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

PriorityLiteral = Literal["LOW", "MEDIUM", "HIGH", "URGENT"]
StatusLiteral = Literal["TODO", "IN_PROGRESS", "DONE", "ARCHIVED"]


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=3, max_length=120)


class WorkspaceUpdate(BaseModel):
    name: str = Field(min_length=3, max_length=120)


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    name: str
    created_at: datetime


class TaskCreate(BaseModel):
    workspace_id: int
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    priority: PriorityLiteral = "MEDIUM"
    due_date: datetime | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    priority: PriorityLiteral | None = None
    status: StatusLiteral | None = None
    due_date: datetime | None = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    owner_id: int
    title: str
    description: str
    priority: str
    status: str
    due_date: datetime | None
    created_at: datetime

class AnalyticsOut(BaseModel):
    total: int
    todo: int
    in_progress: int
    done: int
    archived: int
    urgent_count: int
    completion_rate: float
    cached: bool = False