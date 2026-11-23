from dataclasses import dataclass, field


class AuthorizationError(Exception):
    """Raised when a user attempts to access or modify another tenant's resource."""


class StateConflictError(Exception):
    """Raised when a task state transition violates domain rules."""


@dataclass
class Workspace:
    id: int
    owner_id: int
    name: str

    def __post_init__(self) -> None:
        if not self.name or len(self.name.strip()) < 3:
            raise ValueError("Workspace name must be at least 3 characters")
        self.name = self.name.strip()

    def rename(self, new_name: str, actor_id: int) -> None:
        self.verify_owner(actor_id)
        if not new_name or len(new_name.strip()) < 3:
            raise ValueError("Workspace name must be at least 3 characters")
        self.name = new_name.strip()

    def verify_owner(self, actor_id: int) -> None:
        if self.owner_id != actor_id:
            raise AuthorizationError("Access denied: workspace belongs to another user")


@dataclass
class Task:
    id: int
    workspace_id: int
    owner_id: int
    title: str
    priority: str = "MEDIUM"
    _status: str = "TODO"
    VALID_TRANSITIONS: dict[str, set[str]] = field(
        default_factory=lambda: {
            "TODO": {"IN_PROGRESS", "ARCHIVED"},
            "IN_PROGRESS": {"DONE", "TODO"},
            "DONE": {"ARCHIVED"},
            "ARCHIVED": set(),
        },
        repr=False,
    )

    def __post_init__(self) -> None:
        if not self.title or not self.title.strip():
            raise ValueError("Task title is required")
        self.title = self.title.strip()

        if self.priority not in {"LOW", "MEDIUM", "HIGH", "URGENT"}:
            raise ValueError("Invalid task priority")

        if self._status not in self.VALID_TRANSITIONS:
            raise ValueError("Invalid task status")

    @property
    def status(self) -> str:
        return self._status

    def ensure_owner(self, actor_id: int) -> None:
        if self.owner_id != actor_id:
            raise AuthorizationError("Access denied: task belongs to another user")

    def transition_to(self, new_status: str) -> None:
        if new_status == self._status:
            return
        allowed = self.VALID_TRANSITIONS.get(self._status, set())
        if new_status not in allowed:
            raise StateConflictError(
                f"Illegal transition from {self._status} to {new_status}"
            )
        self._status = new_status