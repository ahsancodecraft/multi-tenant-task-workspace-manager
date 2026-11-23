from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.db.models import UserModel, WorkspaceModel
from app.db.session import get_db
from app.domain.task import Workspace as DomainWorkspace
from app.schemas.task import WorkspaceCreate, WorkspaceResponse, WorkspaceUpdate

router = APIRouter(prefix="/api/workspaces", tags=["Workspaces"])


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: WorkspaceCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    domain_ws = DomainWorkspace(id=0, owner_id=current_user.id, name=payload.name)
    ws_row = WorkspaceModel(owner_id=current_user.id, name=domain_ws.name)
    db.add(ws_row)
    db.commit()
    db.refresh(ws_row)
    return ws_row


@router.get("", response_model=list[WorkspaceResponse])
def list_workspaces(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    return (
        db.query(WorkspaceModel)
        .filter(WorkspaceModel.owner_id == current_user.id)
        .all()
    )


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
def rename_workspace(
    workspace_id: int,
    payload: WorkspaceUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    ws_row = db.query(WorkspaceModel).filter(WorkspaceModel.id == workspace_id).first()
    if not ws_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    domain_ws = DomainWorkspace(id=ws_row.id, owner_id=ws_row.owner_id, name=ws_row.name)
    domain_ws.rename(payload.name, actor_id=current_user.id)

    ws_row.name = domain_ws.name
    db.commit()
    db.refresh(ws_row)
    return ws_row


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    ws_row = db.query(WorkspaceModel).filter(WorkspaceModel.id == workspace_id).first()
    if not ws_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    domain_ws = DomainWorkspace(id=ws_row.id, owner_id=ws_row.owner_id, name=ws_row.name)
    domain_ws.verify_owner(current_user.id)

    db.delete(ws_row)
    db.commit()
    return None