"""
VASAE Predictive Crisis Intelligence Engine
--------------------------------------------
PURE FUNCTIONS — no DB calls, no side effects.

Implements:
1. Velocity Calculation:  velocity = d(tasks)/dt
2. Trend Analysis:        rolling average + growth rate
3. Risk Scoring:          risk = f(velocity, trend, task_density)
4. Hotspot Detection:     identify high-risk regions
5. Urgency Modification:  prediction feeds into scoring

All functions operate on plain data structures for testability.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True)
class TaskSnapshot:
    """Point-in-time task count for a region."""
    region: str
    count: int
    timestamp_epoch: float  # seconds since epoch


@dataclass(frozen=True)
class RegionMetrics:
    """Computed metrics for a single region."""
    region: str
    velocity: float           # d(tasks)/dt — tasks per hour
    trend: str                # "increasing" | "stable" | "decreasing"
    growth_rate: float        # percentage change over window
    rolling_average: float    # avg tasks per window interval
    task_density: int         # current active tasks
    risk_score: float         # composite [0.0 - 1.0]
    predicted_tasks_24h: int  # forecasted new tasks in next 24h
    confidence: float         # prediction confidence [0.0 - 1.0]
    is_hotspot: bool          # risk_score > hotspot_threshold


@dataclass
class PredictionConfig:
    """Tunable parameters for the prediction engine."""
    window_hours: float = 6.0          # Rolling window for trend analysis
    hotspot_threshold: float = 0.65    # Risk score above this = hotspot
    velocity_weight: float = 0.4       # Weight of velocity in risk score
    trend_weight: float = 0.3          # Weight of trend in risk score
    density_weight: float = 0.3        # Weight of density in risk score
    max_velocity: float = 20.0         # Normalization ceiling for velocity
    max_density: int = 50              # Normalization ceiling for density
    min_data_points: int = 2           # Minimum snapshots for valid prediction


DEFAULT_PREDICTION_CONFIG = PredictionConfig()


def compute_velocity(
    snapshots: Sequence[TaskSnapshot],
    window_hours: float = 6.0,
) -> float:
    """
    Compute task arrival velocity: d(tasks)/dt in tasks/hour.

    Uses linear regression slope over the window for stability.
    Falls back to simple difference if < 3 data points.
    """
    if len(snapshots) < 2:
        return 0.0

    sorted_snaps = sorted(snapshots, key=lambda s: s.timestamp_epoch)

    # Time span in hours
    dt_hours = (sorted_snaps[-1].timestamp_epoch - sorted_snaps[0].timestamp_epoch) / 3600.0
    if dt_hours <= 0:
        return 0.0

    if len(sorted_snaps) < 3:
        # Simple difference
        delta_tasks = sorted_snaps[-1].count - sorted_snaps[0].count
        return round(delta_tasks / dt_hours, 4)

    # Linear regression: slope of count vs time
    n = len(sorted_snaps)
    t0 = sorted_snaps[0].timestamp_epoch
    times = [(s.timestamp_epoch - t0) / 3600.0 for s in sorted_snaps]
    counts = [float(s.count) for s in sorted_snaps]

    mean_t = sum(times) / n
    mean_c = sum(counts) / n

    numerator = sum((t - mean_t) * (c - mean_c) for t, c in zip(times, counts))
    denominator = sum((t - mean_t) ** 2 for t in times)

    if abs(denominator) < 1e-9:
        return 0.0

    slope = numerator / denominator
    return round(slope, 4)


def compute_rolling_average(
    snapshots: Sequence[TaskSnapshot],
) -> float:
    """Average task count across all snapshots in window."""
    if not snapshots:
        return 0.0
    return round(sum(s.count for s in snapshots) / len(snapshots), 2)


def compute_growth_rate(
    snapshots: Sequence[TaskSnapshot],
) -> float:
    """
    Percentage growth rate from first to last snapshot.

    Returns 0.0 if baseline is zero.
    """
    if len(snapshots) < 2:
        return 0.0

    sorted_snaps = sorted(snapshots, key=lambda s: s.timestamp_epoch)
    baseline = sorted_snaps[0].count
    current = sorted_snaps[-1].count

    if baseline <= 0:
        return 100.0 if current > 0 else 0.0

    return round(((current - baseline) / baseline) * 100.0, 2)


def classify_trend(velocity: float, growth_rate: float) -> str:
    """
    Classify regional trend based on velocity and growth rate.

    Returns: "increasing" | "stable" | "decreasing"
    """
    if velocity > 0.5 or growth_rate > 10.0:
        return "increasing"
    elif velocity < -0.5 or growth_rate < -10.0:
        return "decreasing"
    return "stable"


def compute_risk_score(
    velocity: float,
    growth_rate: float,
    task_density: int,
    config: PredictionConfig = DEFAULT_PREDICTION_CONFIG,
) -> float:
    """
    Composite risk score for a region.

    risk = w_velocity * norm(velocity) + w_trend * norm(growth) + w_density * norm(density)

    All components normalized to [0, 1], final score clamped to [0, 1].
    """
    # Normalize velocity: map to [0, 1]
    norm_velocity = min(max(velocity, 0.0) / config.max_velocity, 1.0)

    # Normalize growth rate: map [-100, 100] to [0, 1]
    norm_growth = min(max((growth_rate + 100.0) / 200.0, 0.0), 1.0)

    # Normalize density: map to [0, 1]
    norm_density = min(task_density / config.max_density, 1.0)

    raw_risk = (
        config.velocity_weight * norm_velocity
        + config.trend_weight * norm_growth
        + config.density_weight * norm_density
    )

    return round(min(max(raw_risk, 0.0), 1.0), 4)


def predict_tasks_24h(
    velocity: float,
    current_density: int,
    growth_rate: float,
) -> int:
    """
    Forecast new tasks in next 24 hours.

    Uses: predicted = current + velocity * 24 * (1 + growth_rate/100)
    Clamped to non-negative integer.
    """
    growth_factor = 1.0 + max(min(growth_rate, 200.0), -50.0) / 100.0
    predicted = current_density + velocity * 24.0 * growth_factor
    return max(0, round(predicted))


def compute_prediction_confidence(
    data_points: int,
    min_required: int = 2,
    full_confidence_points: int = 20,
) -> float:
    """
    Confidence scales with data availability.

    Ramps linearly from 0.3 at min_required to 0.95 at full_confidence_points.
    """
    if data_points < min_required:
        return 0.1

    if data_points >= full_confidence_points:
        return 0.95

    ratio = (data_points - min_required) / (full_confidence_points - min_required)
    return round(0.3 + 0.65 * ratio, 4)


def analyze_region(
    snapshots: Sequence[TaskSnapshot],
    current_density: int,
    config: PredictionConfig = DEFAULT_PREDICTION_CONFIG,
) -> RegionMetrics:
    """
    Full predictive analysis for a single region.

    Composes all sub-functions into a complete RegionMetrics output.
    """
    if not snapshots:
        region_name = "unknown"
    else:
        region_name = snapshots[0].region

    velocity = compute_velocity(snapshots, config.window_hours)
    rolling_avg = compute_rolling_average(snapshots)
    growth_rate = compute_growth_rate(snapshots)
    trend = classify_trend(velocity, growth_rate)
    risk = compute_risk_score(velocity, growth_rate, current_density, config)
    predicted = predict_tasks_24h(velocity, current_density, growth_rate)
    confidence = compute_prediction_confidence(len(snapshots), config.min_data_points)

    return RegionMetrics(
        region=region_name,
        velocity=velocity,
        trend=trend,
        growth_rate=growth_rate,
        rolling_average=rolling_avg,
        task_density=current_density,
        risk_score=risk,
        predicted_tasks_24h=predicted,
        confidence=confidence,
        is_hotspot=risk >= config.hotspot_threshold,
    )


def detect_hotspots(
    region_metrics: Sequence[RegionMetrics],
    threshold: float | None = None,
) -> list[RegionMetrics]:
    """
    Identify all regions above the hotspot risk threshold.

    Returns list sorted by risk_score descending.
    """
    cutoff = threshold if threshold is not None else DEFAULT_PREDICTION_CONFIG.hotspot_threshold
    hotspots = [m for m in region_metrics if m.risk_score >= cutoff]
    return sorted(hotspots, key=lambda m: m.risk_score, reverse=True)


def compute_urgency_modifier(risk_score: float) -> float:
    """
    Convert a region's risk score into a velocity factor
    that feeds into the scoring engine's urgency component.

    Maps risk [0, 1] → velocity_factor [0, 0.5]
    Only activates when risk > 0.3 to avoid noise.
    """
    if risk_score <= 0.3:
        return 0.0
    return round((risk_score - 0.3) * 0.714, 4)  # maps 0.3→0.0, 1.0→0.5
