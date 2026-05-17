from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Database Engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
    pool_pre_ping=True,  # checks dead connections
    pool_size=10,  # number of persistent connections
    max_overflow=20,  # extra connections if load increases
)

# Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# Dependency for FastAPI routes
async def get_session():
    """
    Provides a database session per request.

    Flow:
    1. Create session
    2. Yield session to route
    3. Close session after request ends
    """

    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db():
    async for session in get_session():
        yield session


# NOTE - Request Flow

# FastAPI Request
#       ↓
# get_db()
#       ↓
# AsyncSession (temporary DB connection)
#       ↓
# Service Layer uses session
#       ↓
# Query executes
#       ↓
# Session closes safely
