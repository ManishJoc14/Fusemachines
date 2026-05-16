from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import asyncio
import time

from app.db.session import get_db, AsyncSessionLocal
from app.services.dashboard_service import DashboardService
from app.schemas.dashboard import CountResponse, OverallCountsResponse

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_count(method_name: str):
    """
    Creates independent DB session for concurrent query.
    """

    async with AsyncSessionLocal() as db:
        service = DashboardService(db)

        method = getattr(service, method_name)

        return await method()


@router.get("/customers/count", response_model=CountResponse)
async def get_customers_count(db: AsyncSession = Depends(get_db)):
    """
    Returns total number of customers.
    """

    logger.info("GET /customers/count called")

    service = DashboardService(db)

    count = await service.count_customers()

    logger.info(f"GET /customers/count completed successfully. Total={count}")

    return {"count": count}


@router.get("/products/count", response_model=CountResponse)
async def get_products_count(db: AsyncSession = Depends(get_db)):
    """
    Returns total number of products.
    """

    logger.info("GET /products/count called")

    service = DashboardService(db)

    count = await service.count_products()

    logger.info(f"GET /products/count completed successfully. Total={count}")

    return {"count": count}


@router.get("/employees/count", response_model=CountResponse)
async def get_employees_count(db: AsyncSession = Depends(get_db)):
    """
    Returns total number of employees.
    """

    logger.info("GET /employees/count called")

    service = DashboardService(db)

    count = await service.count_employees()

    logger.info(f"GET /employees/count completed successfully. Total={count}")

    return {"count": count}


@router.get("/offices/count", response_model=CountResponse)
async def get_offices_count(db: AsyncSession = Depends(get_db)):
    """
    Returns total number of offices.
    """

    logger.info("GET /offices/count called")

    service = DashboardService(db)

    count = await service.count_offices()

    logger.info(f"GET /offices/count completed successfully. Total={count}")

    return {"count": count}


@router.get("/payments/count", response_model=CountResponse)
async def get_payments_count(db: AsyncSession = Depends(get_db)):
    """
    Returns total number of payments.
    """

    logger.info("GET /payments/count called")

    service = DashboardService(db)

    count = await service.count_payments()

    logger.info(f"GET /payments/count completed successfully. Total={count}")

    return {"count": count}


@router.get("/order_details/count", response_model=CountResponse)
async def get_order_details_count(db: AsyncSession = Depends(get_db)):
    """
    Returns total number of order_details.
    """

    logger.info("GET /order_details/count called")

    service = DashboardService(db)

    count = await service.count_order_details()

    logger.info(f"GET /order_details/count completed successfully. Total={count}")

    return {"count": count}


@router.get("/product_lines/count", response_model=CountResponse)
async def get_product_lines_count(db: AsyncSession = Depends(get_db)):
    """
    Returns total number of product_lines.
    """

    logger.info("GET /product_lines/count called")

    service = DashboardService(db)

    count = await service.count_product_lines()

    logger.info(f"GET /product_lines/count completed successfully. Total={count}")

    return {"count": count}


@router.get("/overall_counts", response_model=OverallCountsResponse)
async def get_overall_counts(db: AsyncSession = Depends(get_db)):
    """
    Returns counts from all tables concurrently.
    """

    logger.info("GET /overall_counts called")

    start_time = time.perf_counter()

    service = DashboardService(db)

    logger.info("Starting concurrent count queries")

    results = await asyncio.gather(
        get_count("count_customers"),
        get_count("count_orders"),
        get_count("count_products"),
        get_count("count_employees"),
        get_count("count_offices"),
        get_count("count_payments"),
        get_count("count_order_details"),
        get_count("count_product_lines"),
    )

    logger.info("All concurrent queries completed")

    response_time = time.perf_counter() - start_time

    logger.info(f"/overall_counts completed in {response_time:.4f} seconds")

    return {
        "customers": results[0],
        "orders": results[1],
        "products": results[2],
        "employees": results[3],
        "offices": results[4],
        "payments": results[5],
        "orderdetails": results[6],
        "productlines": results[7],
    }
