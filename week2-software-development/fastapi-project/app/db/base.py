from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base class for all ORM models.

    Every table model (User, Item, etc.)
    will inherit from this class.

    This allows SQLAlchemy to:
    - Track all models
    - Create tables automatically
    - Manage metadata
    """
    pass