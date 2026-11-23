import pytest
from app.core.security import hash_password, verify_password
from app.domain.task import AuthorizationError, StateConflictError, Task, Workspace


def test_task_valid_state_transitions():
    # Arrange
    task = Task(id=1, workspace_id=10, owner_id=1, title="Implement pytest suite")

    # Act & Assert
    assert task.status == "TODO"
    task.transition_to("IN_PROGRESS")
    assert task.status == "IN_PROGRESS"
    task.transition_to("DONE")
    assert task.status == "DONE"
    task.transition_to("ARCHIVED")
    assert task.status == "ARCHIVED"


def test_task_illegal_state_transition_raises_conflict():
    # Arrange
    task = Task(id=2, workspace_id=10, owner_id=1, title="Completed sprint task")
    task.transition_to("ARCHIVED")

    # Act & Assert
    with pytest.raises(StateConflictError):
        task.transition_to("IN_PROGRESS")


def test_task_rejects_blank_title_and_invalid_priority():
    with pytest.raises(ValueError):
        Task(id=3, workspace_id=10, owner_id=1, title="   ")

    with pytest.raises(ValueError):
        Task(id=4, workspace_id=10, owner_id=1, title="Valid Title", priority="CRITICAL")


def test_workspace_owner_verification_and_rename():
    # Arrange
    ws = Workspace(id=1, owner_id=100, name="Engineering")

    # Act
    ws.rename("Platform Engineering", actor_id=100)

    # Assert
    assert ws.name == "Platform Engineering"
    with pytest.raises(AuthorizationError):
        ws.verify_owner(actor_id=999)


def test_argon2_password_hashing_and_salting():
    # Arrange
    raw = "SuperSecretPass123!"

    # Act
    hash_1 = hash_password(raw)
    hash_2 = hash_password(raw)

    # Assert: Unique salts produce different hashes, both verify correctly
    assert hash_1 != raw
    assert hash_1 != hash_2
    assert verify_password(hash_1, raw) is True
    assert verify_password(hash_1, "WrongPassword123!") is False