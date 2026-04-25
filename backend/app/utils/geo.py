"""
VASAE Geo Utilities
-------------------
Pure mathematical functions for geospatial calculations.
ZERO database dependencies — used by scoring engine directly.
"""

import math

# Earth's mean radius in kilometers
EARTH_RADIUS_KM = 6371.0


def haversine_distance(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
) -> float:
    """
    Compute great-circle distance between two GPS coordinates.

    Uses the Haversine formula — accurate for distances up to ~500km
    which covers all realistic volunteer deployment radii.

    Args:
        lat1, lon1: Origin coordinates (degrees)
        lat2, lon2: Destination coordinates (degrees)

    Returns:
        Distance in kilometers (float)
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad)
        * math.cos(lat2_rad)
        * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_KM * c


def proximity_score(distance_km: float, max_radius_km: float = 50.0) -> float:
    """
    Convert raw distance into a 0–1 proximity score.

    Closer = higher score. Beyond max_radius returns 0.

    Args:
        distance_km: Distance between volunteer and task
        max_radius_km: Maximum considered radius

    Returns:
        Score between 0.0 (far) and 1.0 (co-located)
    """
    if distance_km <= 0:
        return 1.0
    if distance_km >= max_radius_km:
        return 0.0
    return 1.0 - (distance_km / max_radius_km)
