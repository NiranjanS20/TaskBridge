"""
VASAE Central Router
--------------------
Aggregates all route modules into a single router.
"""

from fastapi import APIRouter
from app.api.routes import tasks, volunteers, allocation, explain, prediction, learning, simulation, analytics, ws, chat, auth

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(tasks.router)
api_router.include_router(volunteers.router)
api_router.include_router(allocation.router)
api_router.include_router(explain.router)
api_router.include_router(prediction.router)
api_router.include_router(learning.router)
api_router.include_router(simulation.router)
api_router.include_router(analytics.router)
api_router.include_router(ws.router)
api_router.include_router(chat.router)
