"""
VASAE Database Base
-------------------
Declarative base for all SQLAlchemy ORM models.
All models import Base from here to ensure a single metadata registry.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy declarative base class for all VASAE models."""
    pass
