from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.api.deps import require_admin
from app.core.logging_config import logger
from app.db.models import TaskModel, UserModel, WorkspaceModel
from app.db.session import get_db
from app.services.task_service import task_service

router = APIRouter(
    prefix="/api/admin",
    tags=["Admin Oversight"],
    dependencies=[Depends(require_admin)],
)


class AdminOverviewResponse(BaseModel):
    total_users: int
    total_workspaces: int
    total_tasks: int
    urgent_tasks: int
    completed_tasks: int


@router.get("/overview", response_model=AdminOverviewResponse)
def get_admin_overview(
    db: Session = Depends(get_db),
    admin_user: UserModel = Depends(require_admin),
):
    total_users = db.query(UserModel).count()
    total_workspaces = db.query(WorkspaceModel).count()
    total_tasks = db.query(TaskModel).count()
    urgent_tasks = db.query(TaskModel).filter(TaskModel.priority == "URGENT").count()
    completed_tasks = db.query(TaskModel).filter(TaskModel.status == "DONE").count()

    logger.info(f"admin_overview_accessed | admin_id={admin_user.id}")
    return AdminOverviewResponse(
        total_users=total_users,
        total_workspaces=total_workspaces,
        total_tasks=total_tasks,
        urgent_tasks=urgent_tasks,
        completed_tasks=completed_tasks,
    )


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    admin_user: UserModel = Depends(require_admin),
):
    task_row = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    owner_id = task_row.owner_id
    db.delete(task_row)
    db.commit()

    # Invalidate the affected tenant's cached analytics
    task_service.invalidate_user_analytics(owner_id)
    logger.info(
        f"admin_task_removed | admin_id={admin_user.id} | task_id={task_id} | owner_id={owner_id}"
    )
    return None