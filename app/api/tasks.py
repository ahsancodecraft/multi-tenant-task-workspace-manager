from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.core.logging_config import logger
from app.db.models import TaskModel, UserModel, WorkspaceModel
from app.db.session import get_db
from app.domain.task import Task as DomainTask, Workspace as DomainWorkspace
from app.schemas.task import AnalyticsOut, TaskCreate, TaskResponse, TaskUpdate
from app.services.task_service import task_service

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    ws_row = db.query(WorkspaceModel).filter(WorkspaceModel.id == payload.workspace_id).first()
    if not ws_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    domain_ws = DomainWorkspace(id=ws_row.id, owner_id=ws_row.owner_id, name=ws_row.name)
    domain_ws.verify_owner(current_user.id)

    domain_task = DomainTask(
        id=0,
        workspace_id=ws_row.id,
        owner_id=current_user.id,
        title=payload.title,
        priority=payload.priority,
    )

    task_row = TaskModel(
        workspace_id=domain_task.workspace_id,
        owner_id=domain_task.owner_id,
        title=domain_task.title,
        description=payload.description.strip(),
        priority=domain_task.priority,
        status=domain_task.status,
        due_date=payload.due_date,
    )
    db.add(task_row)
    db.commit()
    db.refresh(task_row)

    # Invalidate cached analytics & offload URGENT notification to background job
    task_service.invalidate_user_analytics(current_user.id)
    logger.info(f"task_created | task_id={task_row.id} | user_id={current_user.id} | priority={task_row.priority}")

    if task_row.priority == "URGENT":
        background_tasks.add_task(
            task_service.dispatcher.send_urgent_alert,
            current_user.email,
            task_row.title,
        )

    return task_row


@router.get("", response_model=list[TaskResponse])
def list_tasks(
    status_filter: str | None = Query(default=None, alias="status"),
    priority: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    query = db.query(TaskModel).filter(TaskModel.owner_id == current_user.id)
    if status_filter:
        query = query.filter(TaskModel.status == status_filter)
    if priority:
        query = query.filter(TaskModel.priority == priority)
    return query.all()


@router.get("/analytics", response_model=AnalyticsOut)
def get_tasks_analytics(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    return task_service.get_user_analytics(db=db, user_id=current_user.id)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    task_row = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    domain_task = DomainTask(
        id=task_row.id,
        workspace_id=task_row.workspace_id,
        owner_id=task_row.owner_id,
        title=task_row.title,
        priority=task_row.priority,
        _status=task_row.status,
    )
    domain_task.ensure_owner(current_user.id)
    return task_row


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    task_row = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    domain_task = DomainTask(
        id=task_row.id,
        workspace_id=task_row.workspace_id,
        owner_id=task_row.owner_id,
        title=task_row.title,
        priority=task_row.priority,
        _status=task_row.status,
    )
    domain_task.ensure_owner(current_user.id)

    became_urgent = payload.priority == "URGENT" and task_row.priority != "URGENT"

    if payload.status is not None:
        domain_task.transition_to(payload.status)
        task_row.status = domain_task.status

    if payload.title is not None:
        if not payload.title.strip():
            raise HTTPException(status_code=400, detail="Task title cannot be empty")
        task_row.title = payload.title.strip()

    if payload.description is not None:
        task_row.description = payload.description.strip()

    if payload.priority is not None:
        task_row.priority = payload.priority

    if payload.due_date is not None:
        task_row.due_date = payload.due_date

    db.commit()
    db.refresh(task_row)

    task_service.invalidate_user_analytics(current_user.id)
    logger.info(f"task_updated | task_id={task_row.id} | user_id={current_user.id} | status={task_row.status}")

    if became_urgent:
        background_tasks.add_task(
            task_service.dispatcher.send_urgent_alert,
            current_user.email,
            task_row.title,
        )

    return task_row


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    task_row = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    domain_task = DomainTask(
        id=task_row.id,
        workspace_id=task_row.workspace_id,
        owner_id=task_row.owner_id,
        title=task_row.title,
        priority=task_row.priority,
        _status=task_row.status,
    )
    domain_task.ensure_owner(current_user.id)

    db.delete(task_row)
    db.commit()

    task_service.invalidate_user_analytics(current_user.id)
    logger.info(f"task_deleted | task_id={task_id} | user_id={current_user.id}")
    return None