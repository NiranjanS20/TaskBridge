"""
Role-aware chat service that fetches live system context and calls LLM providers.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.task import Task
from app.models.assignment import Assignment
from app.models.audit import AuditLog
from app.models.volunteer import Volunteer
from app.services.analytics_service import get_analytics_overview
from app.services.prediction_service import predict_all_regions

settings = get_settings()


def _route_query_intent(query: str) -> str:
    q = query.lower()
    if "high risk" in q or "risk zone" in q or "predict" in q:
        return "prediction"
    if "why assign" in q or "why assigned" in q or "explain" in q:
        return "explain"
    if "analytics" in q or "fairness" in q or "performance" in q:
        return "analytics"
    if "task" in q:
        return "tasks"
    if "volunteer" in q:
        return "volunteers"
    return "general"


async def _live_context(
    db: AsyncSession,
    query: str,
    role: str,
    user_id: str | None,
    ngo_id: str | None,
) -> dict[str, Any]:
    intent = _route_query_intent(query)
    context: dict[str, Any] = {"intent": intent, "role": role}

    if intent == "tasks":
        query_stmt = select(Task)
        if ngo_id:
            query_stmt = query_stmt.where(Task.ngo_id == ngo_id)
        result = await db.execute(query_stmt.order_by(Task.created_at.desc()).limit(10))
        tasks = result.scalars().all()
        context["tasks"] = [
            {
                "id": t.id,
                "title": t.title,
                "status": t.status,
                "urgency": t.urgency,
                "region": t.region,
            }
            for t in tasks
        ]
    elif intent == "prediction":
        metrics = await predict_all_regions(db)
        context["predictions"] = [
            {
                "region": m.region,
                "risk_score": m.risk_score,
                "trend": m.trend,
                "predicted_tasks_24h": m.predicted_tasks_24h,
            }
            for m in metrics[:10]
        ]
    elif intent == "explain":
        audit_query = select(AuditLog)
        if ngo_id:
            audit_query = audit_query.join(Task, Task.id == AuditLog.task_id).where(Task.ngo_id == ngo_id)
        latest_audit = await db.execute(audit_query.order_by(AuditLog.created_at.desc()).limit(1))
        audit = latest_audit.scalar_one_or_none()
        context["latest_explain"] = {
            "task_id": audit.task_id if audit else None,
            "reason": audit.reason if audit else "No explainability logs yet.",
            "confidence": audit.confidence_score if audit else None,
            "factors": audit.factors if audit else {},
        }
    elif intent == "volunteers":
        if role.upper() == "VOLUNTEER" and user_id:
            result = await db.execute(
                select(Assignment, Task)
                .join(Task, Task.id == Assignment.task_id)
                .where(Assignment.volunteer_id == user_id)
                .order_by(Assignment.assigned_at.desc())
                .limit(10)
            )
            context["my_assignments"] = [
                {
                    "task_id": task.id,
                    "title": task.title,
                    "status": assignment.status,
                    "assigned_at": assignment.assigned_at.isoformat(),
                }
                for assignment, task in result.all()
            ]
        else:
            vol_query = select(Volunteer)
            if ngo_id:
                vol_query = vol_query.where(Volunteer.ngo_id == ngo_id)
            result = await db.execute(vol_query.order_by(Volunteer.updated_at.desc()).limit(10))
            context["volunteers"] = [
                {
                    "id": v.id,
                    "name": v.name,
                    "status": v.status,
                    "burnout_score": v.burnout_score,
                }
                for v in result.scalars().all()
            ]
    else:
        context["analytics"] = await get_analytics_overview(db, ngo_id=ngo_id)
    return context


def _fallback_answer(query: str, context: dict[str, Any]) -> str:
    intent = context.get("intent", "general")
    if intent == "tasks":
        tasks = context.get("tasks", [])
        if not tasks:
            return "No tasks are currently available for your NGO scope."
        first = tasks[0]
        return f"Top task now is '{first.get('title', 'Untitled')}' with status {first.get('status', 'unknown')} and urgency {first.get('urgency', 'n/a')}."
    if intent == "volunteers":
        volunteers = context.get("volunteers", [])
        if not volunteers:
            return "No volunteer records are available in the current scope."
        return f"I found {len(volunteers)} recent volunteer records. Highest burnout in view is {max(v.get('burnout_score', 0) for v in volunteers):.2f}."
    if intent == "analytics":
        analytics = context.get("analytics", {})
        return (
            f"Total tasks: {analytics.get('total_tasks', 0)}, completed tasks: {analytics.get('completed_tasks', 0)}, "
            f"avg response: {analytics.get('avg_response_time', 0)}s, fairness (Gini): {analytics.get('gini_coefficient', 0)}."
        )
    return "I can help with task status, volunteer load, explainability, predictions, and analytics in your NGO scope."


async def _call_gemini(prompt: str) -> str:
    if not settings.GEMINI_API_KEY:
        return "Gemini API key is not configured."
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-1.5-flash:generateContent"
    )
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{url}?key={settings.GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
        )
        response.raise_for_status()
        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return "No response from Gemini."
        return candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "No response text.")


async def _call_groq(prompt: str) -> str:
    if not settings.GROQ_API_KEY:
        return "Groq API key is not configured."
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            return "No response from Groq."
        return choices[0].get("message", {}).get("content", "No response text.")


async def answer_query(
    db: AsyncSession,
    *,
    query: str,
    role: str,
    user_id: str | None = None,
    ngo_id: str | None = None,
) -> dict[str, Any]:
    context = await _live_context(db, query, role, user_id, ngo_id)
    prompt = (
        "You are VASAE Assistant. Answer based only on context.\n"
        f"Role: {role}\n"
        f"User Query: {query}\n"
        f"Context JSON: {json.dumps(context)}\n"
        "Respond clearly in 4-8 sentences with actionable insight."
    )
    provider = settings.CHAT_LLM_PROVIDER.lower().strip()
    if provider == "groq" and settings.GROQ_API_KEY:
        answer = await _call_groq(prompt)
    elif settings.GEMINI_API_KEY:
        answer = await _call_gemini(prompt)
    else:
        answer = _fallback_answer(query, context)
        provider = "fallback"
    return {
        "provider": provider,
        "intent": context.get("intent"),
        "answer": answer,
        "context": context,
    }
