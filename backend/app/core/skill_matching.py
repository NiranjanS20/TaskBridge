"""
Semantic skill matching utilities for task-volunteer alignment.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from app.utils.logger import get_logger

logger = get_logger(__name__)

_EMBED_DIM = 256
_TOKEN_RE = re.compile(r"[a-z0-9_]+")
_embedding_cache: dict[str, list[float]] = {}
_SYNONYM_MAP = {
    "doctor": ["medical", "healthcare", "medic"],
    "nurse": ["medical", "healthcare", "medic"],
    "medic": ["medical", "healthcare"],
    "first": ["aid"],
    "aid": ["medical", "support"],
    "logistics": ["supply", "chain", "operations"],
    "supply": ["logistics", "distribution"],
    "rescue": ["search", "emergency", "response"],
}


def _normalize_text(text: str) -> str:
    return (text or "").strip().lower()


def _tokenize(text: str) -> list[str]:
    tokens = _TOKEN_RE.findall(_normalize_text(text))
    expanded = list(tokens)
    for token in tokens:
        expanded.extend(_SYNONYM_MAP.get(token, []))
    return expanded


def _fallback_keyword_match(task_text: str, volunteer_skills: list[str]) -> float:
    required = set(_tokenize(task_text))
    available = set(_tokenize(" ".join(volunteer_skills or [])))
    if not required:
        return 1.0
    if not available:
        return 0.0
    return max(0.0, min(1.0, len(required & available) / len(required)))


def generate_embedding(text: str) -> list[float]:
    """
    Build a lightweight hashed TF embedding for text.
    Cached in-memory for hot-path allocation scoring.
    """
    normalized = _normalize_text(text)
    if not normalized:
        return [0.0] * _EMBED_DIM
    cached = _embedding_cache.get(normalized)
    if cached is not None:
        return cached

    tokens = _tokenize(normalized)
    if not tokens:
        vector = [0.0] * _EMBED_DIM
        _embedding_cache[normalized] = vector
        return vector

    counts = Counter(tokens)
    vector = [0.0] * _EMBED_DIM
    total = float(sum(counts.values())) or 1.0
    for token, count in counts.items():
        idx = hash(token) % _EMBED_DIM
        vector[idx] += float(count) / total

    _embedding_cache[normalized] = vector
    return vector


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(a * a for a in vec_a))
    mag_b = math.sqrt(sum(b * b for b in vec_b))
    if mag_a <= 1e-12 or mag_b <= 1e-12:
        return 0.0
    return dot / (mag_a * mag_b)


def compute_skill_similarity(task_text: str, volunteer_skills: list[str]) -> float:
    """
    Semantic similarity score in [0, 1] with keyword fallback.
    """
    if not task_text.strip():
        return 1.0
    if not volunteer_skills:
        return 0.0

    try:
        task_vec = generate_embedding(task_text)
        volunteer_vec = generate_embedding(" ".join(volunteer_skills))
        similarity = _cosine_similarity(task_vec, volunteer_vec)
        if math.isnan(similarity) or math.isinf(similarity):
            raise ValueError("Invalid semantic similarity value")
        return max(0.0, min(1.0, float(similarity)))
    except Exception as exc:
        logger.warning("Semantic skill matching fallback triggered: %s", exc)
        return _fallback_keyword_match(task_text, volunteer_skills)
