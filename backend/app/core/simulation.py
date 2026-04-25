"""
Synthetic crisis scenario generation primitives.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass

from app.core.scoring import TaskScoreInput


@dataclass(frozen=True)
class SimulationTaskBlueprint:
    title: str
    description: str
    category: str
    required_skills: list[str]
    urgency: int
    complexity: int
    team_size: int
    latitude: float
    longitude: float
    region: str


_SCENARIO_TEMPLATES: dict[str, list[dict]] = {
    "flood": [
        {"title": "Evacuation support", "skills": ["rescue", "logistics"], "category": "rescue"},
        {"title": "Medical triage camp", "skills": ["medical", "first aid"], "category": "medical"},
        {"title": "Relief distribution", "skills": ["logistics", "coordination"], "category": "logistics"},
    ],
    "medical": [
        {"title": "Emergency response", "skills": ["medical", "triage"], "category": "medical"},
        {"title": "Patient transport", "skills": ["transport", "medical"], "category": "medical"},
        {"title": "Clinic support", "skills": ["nursing", "healthcare"], "category": "medical"},
    ],
    "fire": [
        {"title": "Fire containment support", "skills": ["firefighting", "rescue"], "category": "rescue"},
        {"title": "Evacuation routing", "skills": ["logistics", "crowd control"], "category": "logistics"},
        {"title": "First responder aid", "skills": ["first aid", "medical"], "category": "medical"},
    ],
}


def generate_synthetic_tasks(
    *,
    region: str,
    scenario_type: str,
    task_count: int,
    duration_seconds: int,
    base_latitude: float,
    base_longitude: float,
    prediction_bias: float = 0.0,
) -> list[SimulationTaskBlueprint]:
    templates = _SCENARIO_TEMPLATES.get(scenario_type.lower()) or _SCENARIO_TEMPLATES["flood"]
    tasks: list[SimulationTaskBlueprint] = []

    urgency_boost = 1 if prediction_bias > 0.2 else 0
    complexity_boost = 1 if prediction_bias > 0.35 else 0

    for _ in range(max(task_count, 1)):
        template = random.choice(templates)
        lat = base_latitude + random.uniform(-0.05, 0.05)
        lon = base_longitude + random.uniform(-0.05, 0.05)
        urgency = min(5, random.randint(2, 5) + urgency_boost)
        complexity = min(10, random.randint(3, 8) + complexity_boost)
        team_size = 1 if random.random() < 0.8 else 2
        title = template["title"]
        description = f"{title} required in {region} due to {scenario_type} conditions."
        tasks.append(
            SimulationTaskBlueprint(
                title=title,
                description=description,
                category=template["category"],
                required_skills=template["skills"],
                urgency=urgency,
                complexity=complexity,
                team_size=team_size,
                latitude=lat,
                longitude=lon,
                region=region,
            )
        )
    return tasks


def blueprint_to_score_input(blueprint: SimulationTaskBlueprint) -> TaskScoreInput:
    return TaskScoreInput(
        id=str(uuid.uuid4()),
        required_skills=blueprint.required_skills,
        urgency=blueprint.urgency,
        complexity=blueprint.complexity,
        latitude=blueprint.latitude,
        longitude=blueprint.longitude,
        waiting_time_minutes=0.0,
        team_size=blueprint.team_size,
        region=blueprint.region,
    )
