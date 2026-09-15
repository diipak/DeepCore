from typing import Optional
from fastapi import Header, Depends, HTTPException, status
from sqlalchemy.orm import Session
from deepcore2.storage.sqlite.db import get_db
from deepcore2.storage.sqlite.models import Workspace as DBWorkspace
from deepcore2.core.objects.schemas import ExecutionContext

class WorkspaceResolver:
    @staticmethod
    def resolve(db: Session, x_workspace_uuid: Optional[str] = None) -> ExecutionContext:
        if not x_workspace_uuid:
            personal_ws = db.query(DBWorkspace).filter(DBWorkspace.name == "Personal Workspace").first()
            if not personal_ws:
                personal_ws = DBWorkspace(name="Personal Workspace")
                db.add(personal_ws)
                db.commit()
                db.refresh(personal_ws)
            return ExecutionContext(
                workspace_id=personal_ws.id,
                workspace_uuid=personal_ws.uuid,
                workspace_name=personal_ws.name
            )
        
        ws = db.query(DBWorkspace).filter(DBWorkspace.uuid == x_workspace_uuid).first()
        if not ws:
            raise HTTPException(
                status_code=404,
                detail=f"Workspace with UUID '{x_workspace_uuid}' not found."
            )
        return ExecutionContext(
            workspace_id=ws.id,
            workspace_uuid=ws.uuid,
            workspace_name=ws.name
        )

def get_execution_context(
    db: Session = Depends(get_db),
    x_workspace_uuid: Optional[str] = Header(None)
) -> ExecutionContext:
    return WorkspaceResolver.resolve(db, x_workspace_uuid)
