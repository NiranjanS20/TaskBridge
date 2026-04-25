"""
VASAE Ingestion Service
-----------------------
Orchestrates the task creation pipeline:
  Raw input -> Intelligence processing -> Structured Task in DB

This is the SERVICE layer — it connects routes to core logic and DB.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.task import Task
from app.schemas.task_schema import (
    TaskUploadRequest,
    TaskCreateRequest,
    TaskResponse,
    TaskUpdateRequest,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def create_task_from_structured(
    db: AsyncSession,
    data: TaskCreateRequest,
    ngo_id: str | None = None,
) -> Task:
    """
    Create a task from structured input (bypasses NLP).

    Args:
        db: Database session
        data: Validated task creation request

    Returns:
        Created Task ORM object
    """
    task = Task(
        ngo_id=ngo_id,
        title=data.title,
        description=data.description,
        category=data.category,
        required_skills=data.required_skills,
        urgency=data.urgency,
        complexity=data.complexity,
        team_size=data.team_size,
        latitude=data.latitude,
        longitude=data.longitude,
        region=data.region,
        status="pending",
    )
    db.add(task)
    await db.flush()  # Get ID without committing

    logger.info(f"Task created: {task.id[:8]} - '{task.title}' [urgency={task.urgency}]")
    return task


async def create_task_from_raw(
    db: AsyncSession,
    data: TaskUploadRequest,
    ngo_id: str | None = None,
) -> Task:
    """
    Create a task from raw unstructured input.
    Stores the raw text; NLP processing happens in a separate step.

    Args:
        db: Database session
        data: Raw upload request

    Returns:
        Created Task ORM object (status=processing)
    """
    task = Task(
        ngo_id=ngo_id,
        title="Unprocessed Task",
        raw_input=data.raw_input,
        latitude=data.latitude,
        longitude=data.longitude,
        region=data.region,
        status="processing",
    )
    db.add(task)
    await db.flush()

    logger.info(f"Raw task ingested: {task.id[:8]} — awaiting NLP processing")
    return task


async def get_task_by_id(db: AsyncSession, task_id: str, ngo_id: str | None = None) -> Task | None:
    """Fetch a single task by ID."""
    query = select(Task).where(Task.id == task_id)
    if ngo_id:
        query = query.where(Task.ngo_id == ngo_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_pending_tasks(db: AsyncSession) -> list[Task]:
    """Fetch all tasks in 'pending' status for allocation."""
    result = await db.execute(
        select(Task).where(Task.status == "pending").order_by(Task.created_at)
    )
    return list(result.scalars().all())


async def get_all_tasks(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 50,
    ngo_id: str | None = None,
) -> tuple[list[Task], int]:
    """Paginated task list."""
    # Count
    from sqlalchemy import func
    count_query = select(func.count(Task.id))
    if ngo_id:
        count_query = count_query.where(Task.ngo_id == ngo_id)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Fetch page
    offset = (page - 1) * page_size
    query = select(Task)
    if ngo_id:
        query = query.where(Task.ngo_id == ngo_id)
    result = await db.execute(
        query.order_by(Task.created_at.desc()).offset(offset).limit(page_size)
    )
    tasks = list(result.scalars().all())

    return tasks, total


async def update_task(
    db: AsyncSession,
    task_id: str,
    data: TaskUpdateRequest,
    ngo_id: str | None = None,
) -> Task | None:
    """Partially update a task."""
    task = await get_task_by_id(db, task_id, ngo_id=ngo_id)
    if not task:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    await db.flush()
    logger.info(f"Task {task_id[:8]} updated: {list(update_data.keys())}")
    return task
