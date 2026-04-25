"""
VASAE Tasks API Routes
----------------------
Thin controllers — all business logic delegated to services.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.dependencies import get_current_user, require_roles
from app.models.user import User
from app.schemas.task_schema import (
    TaskUploadRequest,
    TaskCreateRequest,
    TaskResponse,
    TaskListResponse,
    TaskUpdateRequest,
)
from app.services import ingestion_service, intelligence_service
from app.services.auth_service import ROLE_NGO_ADMIN, ROLE_NGO_MANAGER
from app.events.event_dispatcher import (
    publish,
    EVENT_CANCELLATION,
    EVENT_NEW_TASK,
    EVENT_URGENCY_CHANGE,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/upload", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def upload_task(
    data: TaskUploadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_NGO_ADMIN, ROLE_NGO_MANAGER)),
):
    """
    Upload a raw unstructured task from NGO input.
    Creates the task record and triggers NLP processing.
    """
    task = await ingestion_service.create_task_from_raw(db, data, ngo_id=current_user.ngo_id)
    await db.commit()

    # Fire event — triggers intelligence processing pipeline
    await publish(EVENT_NEW_TASK, {"task_id": task.id, "type": "raw", "ngo_id": current_user.ngo_id})

    return TaskResponse.model_validate(task)


@router.post("/create", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_NGO_ADMIN, ROLE_NGO_MANAGER)),
):
    """Create a structured task (bypasses NLP)."""
    task = await ingestion_service.create_task_from_structured(db, data, ngo_id=current_user.ngo_id)
    await db.commit()

    # Fire event — triggers allocation cycle
    await publish(EVENT_NEW_TASK, {"task_id": task.id, "type": "structured", "ngo_id": current_user.ngo_id})

    return TaskResponse.model_validate(task)


@router.post("/process/{task_id}", response_model=TaskResponse)
async def process_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_NGO_ADMIN, ROLE_NGO_MANAGER)),
):
    """Run NLP intelligence processing on a raw task."""
    task = await ingestion_service.get_task_by_id(db, task_id, ngo_id=current_user.ngo_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if not task.raw_input:
        raise HTTPException(status_code=400, detail="Task has no raw input to process")

    enriched = await intelligence_service.process_task(db, task)
    await db.commit()

    # Now it's pending — fire event for allocation
    await publish(EVENT_NEW_TASK, {"task_id": enriched.id, "type": "processed", "ngo_id": current_user.ngo_id})

    return TaskResponse.model_validate(enriched)


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all tasks with pagination."""
    tasks, total = await ingestion_service.get_all_tasks(db, page, page_size, ngo_id=current_user.ngo_id)
    return TaskListResponse(
        tasks=[TaskResponse.model_validate(t) for t in tasks],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single task by ID."""
    task = await ingestion_service.get_task_by_id(db, task_id, ngo_id=current_user.ngo_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return TaskResponse.model_validate(task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    data: TaskUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_NGO_ADMIN, ROLE_NGO_MANAGER)),
):
    """Update a task. Fires urgency_change event if urgency modified."""
    task = await ingestion_service.update_task(db, task_id, data, ngo_id=current_user.ngo_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    await db.commit()

    if data.urgency is not None:
        await publish(EVENT_URGENCY_CHANGE, {"task_id": task_id, "new_urgency": data.urgency, "ngo_id": current_user.ngo_id})

    if data.status == "cancelled":
        await publish(EVENT_CANCELLATION, {"task_id": task_id, "reason": "task_status_cancelled", "ngo_id": current_user.ngo_id})

    return TaskResponse.model_validate(task)
