"""
Simulation API routes.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services import simulation_service

router = APIRouter(prefix="/simulate", tags=["Simulation"])


class SimulationStartRequest(BaseModel):
    region: str = Field(..., min_length=1)
    scenario_type: str = Field(..., pattern="^(flood|medical|fire)$")
    task_count: int = Field(default=20, ge=1, le=300)
    duration_seconds: int = Field(default=30, ge=5, le=1800)
    sandbox: bool = True


@router.post("/start")
async def start_simulation(
    data: SimulationStartRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        sim_id = await simulation_service.start_simulation(
            db=db,
            region=data.region,
            scenario_type=data.scenario_type,
            task_count=data.task_count,
            duration_seconds=data.duration_seconds,
            sandbox=data.sandbox,
        )
        return {"simulation_id": sim_id, "status": "started", "sandbox": data.sandbox}
    except ValueError as exc:
        raise HTTPException(status_code=429, detail=str(exc))


@router.get("/{simulation_id}/status")
async def simulation_status(simulation_id: str):
    status = simulation_service.get_simulation_status(simulation_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return status


@router.get("/{simulation_id}/results")
async def simulation_results(simulation_id: str):
    results = simulation_service.get_simulation_results(simulation_id)
    if results is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return results


@router.get("/{simulation_id}/stream")
async def simulation_stream(simulation_id: str):
    return StreamingResponse(
        simulation_service.stream_simulation(simulation_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
