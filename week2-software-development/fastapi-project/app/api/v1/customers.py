from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.db.session import get_db
from app.schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
    CustomerDeleteResponse,
)
from app.schemas.order import OrderResponse
from app.schemas.payment import PaymentResponse
from app.services.customer_service import CustomerService

router = APIRouter()


@router.get("/", response_model=list[CustomerResponse])
async def get_all_customers(db: AsyncSession = Depends(get_db)):
    """
    Returns all customers.
    """

    service = CustomerService(db)
    customers = await service.get_all_customers()

    return customers


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer_by_id(customer_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get customer by ID.
    """

    service = CustomerService(db)

    customer = await service.get_customer_by_id(customer_id)

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found"
        )

    return customer


@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(data: CustomerCreate, db: AsyncSession = Depends(get_db)):
    """
    Create new customer.
    """

    service = CustomerService(db)

    return await service.create_customer(data)


@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: int,
    data: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update existing customer.
    """

    service = CustomerService(db)

    updated = await service.update_customer(customer_id, data)

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found"
        )

    return updated


@router.delete("/{customer_id}", response_model=CustomerDeleteResponse)
async def delete_customer(customer_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete customer.
    """

    service = CustomerService(db)

    deleted = await service.delete_customer(customer_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found"
        )

    return {"message": "Customer deleted successfully"}


@router.get("/{customer_id}/orders", response_model=list[OrderResponse])
async def get_customer_orders(customer_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get all orders for a customer.
    """

    service = CustomerService(db)

    return await service.get_customer_orders(customer_id)


@router.get("/{customer_id}/payments", response_model=list[PaymentResponse])
async def get_customer_payments(customer_id: int, db:AsyncSession = Depends(get_db)):
    """
    Get all payments for a customer.
    """

    service = CustomerService(db)

    return await service.get_customer_payments(customer_id)

