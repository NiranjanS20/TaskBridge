"""
VASAE Intelligence Service
--------------------------
NLP/AI processing layer that enriches raw tasks.

In production, this would call an LLM API (e.g., OpenAI, Gemini)
to extract structured data from unstructured NGO reports.

For now: rule-based extraction (mock-ready for LLM integration).
"""

from app.models.task import Task
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Keyword-to-category mapping (rule-based fallback)
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "medical": ["medical", "doctor", "hospital", "injury", "wound", "health", "medicine", "ambulance"],
    "logistics": ["supply", "transport", "deliver", "food", "water", "provisions", "cargo"],
    "search_rescue": ["search", "rescue", "trapped", "missing", "debris", "collapse"],
    "shelter": ["shelter", "housing", "tent", "camp", "evacuation", "displaced"],
    "communication": ["communication", "radio", "signal", "network", "connectivity"],
}

SKILL_KEYWORDS: dict[str, list[str]] = {
    "medical": ["medical", "doctor", "nurse", "surgeon", "paramedic", "first_aid"],
    "logistics": ["logistics", "driving", "transport", "supply_chain"],
    "search_rescue": ["search_rescue", "climbing", "diving", "heavy_machinery"],
    "engineering": ["engineering", "electrical", "construction", "plumbing"],
    "communication": ["communication", "translation", "radio_operator"],
}


def extract_category(text: str) -> str:
    """Extract task category from raw text using keyword matching."""
    text_lower = text.lower()

    scores: dict[str, int] = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[category] = score

    if scores:
        return max(scores, key=scores.get)  # type: ignore
    return "general"


def extract_skills(text: str) -> list[str]:
    """Extract required skills from raw text."""
    text_lower = text.lower()
    skills: list[str] = []

    for skill, keywords in SKILL_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            skills.append(skill)

    return skills if skills else ["general"]


def estimate_urgency(text: str) -> int:
    """Estimate urgency 1-5 from text sentiment/keywords."""
    text_lower = text.lower()

    critical_words = ["critical", "emergency", "urgent", "dying", "life-threatening", "immediate"]
    high_words = ["serious", "severe", "important", "asap", "quickly"]
    medium_words = ["needed", "required", "help", "assist"]

    if any(w in text_lower for w in critical_words):
        return 5
    if any(w in text_lower for w in high_words):
        return 4
    if any(w in text_lower for w in medium_words):
        return 3
    return 2


def estimate_complexity(text: str) -> int:
    """Estimate complexity 1-10 from text content."""
    text_lower = text.lower()
    complexity = 5  # baseline

    # Complexity modifiers
    if any(w in text_lower for w in ["surgery", "hazardous", "dangerous", "technical"]):
        complexity += 3
    if any(w in text_lower for w in ["multiple", "large-scale", "coordination"]):
        complexity += 2
    if any(w in text_lower for w in ["simple", "basic", "routine"]):
        complexity -= 2

    return max(1, min(10, complexity))


async def process_task(db: AsyncSession, task: Task) -> Task:
    """
    Process a raw task through the intelligence pipeline.

    Extracts:
    - Category
    - Required skills
    - Urgency estimate
    - Complexity estimate
    - Title (first 80 chars of processed description)

    Args:
        db: Database session
        task: Task with raw_input to process

    Returns:
        Enriched Task object
    """
    if not task.raw_input:
        logger.warning(f"Task {task.id[:8]}: no raw input to process")
        return task

    raw = task.raw_input

    task.category = extract_category(raw)
    task.required_skills = extract_skills(raw)
    task.urgency = estimate_urgency(raw)
    task.complexity = estimate_complexity(raw)
    task.title = raw[:80].strip().replace("\n", " ")
    task.description = raw
    task.status = "pending"  # Ready for allocation

    await db.flush()

    logger.info(
        f"Task {task.id[:8]} processed: category={task.category}, "
        f"urgency={task.urgency}, skills={task.required_skills}"
    )
    return task
