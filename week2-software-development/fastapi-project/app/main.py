from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.logging import setup_logging
from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import engine
from app.db.base import Base


# Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events.
    """

    # STARTUP
    setup_logging()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("Application started successfully")

    yield

    # SHUTDOWN
    await engine.dispose()
    print("Application shutdown complete")


# App factory
def create_app() -> FastAPI:
    """
    Creates and configures the FastAPI application.
    """

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        lifespan=lifespan,
    )

    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(api_router, prefix="/api/v1")

    return app


# App instance
app = create_app()
