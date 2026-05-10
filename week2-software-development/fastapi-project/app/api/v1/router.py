from fastapi import APIRouter

from app.api.v1 import customers
from app.api.v1 import dashboard

api_router = APIRouter()

api_router.include_router(
    dashboard.router,
    prefix="",
    tags=["Dashboard Counts"],
)

api_router.include_router(
    customers.router,
    prefix="/customers",
    tags=["customers"],
)
