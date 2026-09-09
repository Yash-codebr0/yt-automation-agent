from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from backend.app.core.database import get_db
from backend.app.models.project import Project
from backend.app.models.log import AgentLog
from backend.app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate, AgentLogOut
from backend.app.api.deps import get_current_user
from backend.app.models.user import User

router = APIRouter()

@router.get("/", response_model=List[ProjectOut])
def read_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all projects created by the authenticated user."""
    return db.query(Project).filter(Project.user_id == current_user.id).order_by(Project.created_at.desc()).all()

@router.get("/{project_id}", response_model=ProjectOut)
def read_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve detailed project configuration and assets."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

def dispatch_workflow(project_id: str):
    """Dispatches workflow execution to Celery if active, otherwise runs in background thread."""
    use_celery = False
    try:
        from backend.app.core.celery_app import celery_app
        inspector = celery_app.control.inspect(timeout=1.0)
        workers = inspector.ping() if inspector else None
        if workers:
            use_celery = True
    except Exception as inspect_err:
        print(f"Celery worker check warning: {inspect_err}")

    from backend.app.tasks.workflow_tasks import run_project_workflow_task

    if use_celery:
        print(f"Dispatching project {project_id} workflow to active Celery worker...")
        task = run_project_workflow_task.delay(project_id)
        return {"task_id": task.id, "status": "running", "mode": "celery"}
    else:
        print(f"No active Celery worker detected. Running project {project_id} in background thread...")
        import threading
        thread = threading.Thread(target=run_project_workflow_task, args=(project_id,))
        thread.daemon = True
        thread.start()
        return {"task_id": "thread-execution", "status": "running", "mode": "thread"}


@router.post("/", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    project_in: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new empire project under the user account."""
    youtube_account_id = project_in.youtube_account_id
    if not youtube_account_id:
        from backend.app.models.youtube_account import YouTubeAccount
        active_acc = db.query(YouTubeAccount).filter(
            YouTubeAccount.user_id == current_user.id,
            YouTubeAccount.is_active == True
        ).first()
        if active_acc:
            youtube_account_id = active_acc.id

    # If no trend_id is given or is_custom is explicitly set, mark as custom project
    is_custom = project_in.is_custom or (project_in.trend_id is None)
    custom_title = project_in.custom_title or (project_in.title if is_custom else None)

    project = Project(
        title=project_in.title,
        niche=project_in.niche,
        trend_id=project_in.trend_id,
        youtube_account_id=youtube_account_id,
        user_id=current_user.id,
        is_custom=is_custom,
        custom_title=custom_title,
        status="draft"
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    
    # Initialize first log
    log_entry = AgentLog(
        project_id=project.id,
        agent_name="System",
        status="info",
        log_message="Project initialized. Ready to execute automation agents."
    )
    db.add(log_entry)
    db.commit()
    
    return project

@router.put("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: str,
    project_in: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update project attributes (such as manual script edits or scheduling)."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    update_data = project_in.dict(exclude_unset=True)
    for field in update_data:
        setattr(project, field, update_data[field])
        
    db.commit()
    db.refresh(project)
    return project

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a project and associated agent logs."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    # Delete logs first
    db.query(AgentLog).filter(AgentLog.project_id == project_id).delete()
    db.delete(project)
    db.commit()
    return None

@router.post("/{project_id}/run", status_code=status.HTTP_202_ACCEPTED)
def run_workflow(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Kick off the background LangGraph multi-agent flow."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    if project.status == "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow is already running for this project."
        )
        
    from backend.app.core.redis_lock import acquire_project_lock
    if not acquire_project_lock(project_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A workflow execution lock is already active for this project."
        )
        
    project.status = "running"
    db.commit()

    return dispatch_workflow(project_id)



@router.get("/{project_id}/logs", response_model=List[AgentLogOut])
def read_project_logs(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve real-time audit logs of the agents for the project."""
    # Verify project ownership
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    return db.query(AgentLog).filter(AgentLog.project_id == project_id).order_by(AgentLog.created_at.asc()).all()

@router.post("/{project_id}/approve")
def approve_workflow(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve the generated draft/video and resume publishing execution."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    if project.status != "waiting_for_approval":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project is not waiting for approval."
        )
        
    project.status = "running"
    db.commit()
    
    # Log approval and trigger resume
    from backend.app.models.log import AgentLog
    log_entry = AgentLog(
        project_id=project.id,
        agent_name="System",
        status="info",
        log_message="Human approval received. Resuming publishing pipeline."
    )
    db.add(log_entry)
    db.commit()
    
    dispatch_res = dispatch_workflow(project_id)
    return {"status": "resumed", **dispatch_res}

@router.post("/{project_id}/reject")
def reject_workflow(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reject the generated video, resetting state to draft for manual editing."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    if project.status != "waiting_for_approval":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project is not waiting for approval."
        )
        
    project.status = "draft"
    db.commit()
    
    # Log rejection
    from backend.app.models.log import AgentLog
    log_entry = AgentLog(
        project_id=project.id,
        agent_name="System",
        status="info",
        log_message="Human rejection received. Resetting project status to draft."
    )
    db.add(log_entry)
    db.commit()
    
    return {"status": "rejected"}

