from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.customer import Customer
from app.models.order import Order
from app.models.payment import Payment

from app.schemas.customer import CustomerCreate, CustomerUpdate

import logging

logger = logging.getLogger(__name__)


class CustomerService:
    """
    Business logic layer for Customer operations.

    It only deals with database logic and domain rules.
    This layer is independent of HTTP.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_customers(self):
        """
        Fetch all customers.
        """

        logger.info("Fetching all customers from database")

        result = await self.db.execute(select(Customer))
        customers = result.scalars().all()

        logger.info(f"Fetched {len(customers)} customers")

        return customers

    async def get_customer_by_id(self, customer_id: int):
        """
        Fetch single customer by primary key.
        """

        logger.info(f"Fetching customer with ID={customer_id}")

        result = await self.db.execute(
            select(Customer).where(Customer.customerNumber == customer_id)
        )
        customer = result.scalars().first()

        if customer:
            logger.info(f"Customer found: ID={customer_id}")
        else:
            logger.warning(f"Customer not found: ID={customer_id}")

        return customer

    async def create_customer(self, data: CustomerCreate):
        """
        Create a new customer record.
        """

        logger.info("Creating new customer")

        new_customer = Customer(**data.model_dump())

        self.db.add(new_customer)
        await self.db.commit()
        await self.db.refresh(new_customer)

        logger.info(f"Customer created: ID={new_customer.customerNumber}")

        return new_customer

    async def update_customer(self, customer_id: int, data: CustomerUpdate):
        """
        Partial update of customer fields.
        """

        logger.info(f"Updating customer ID={customer_id}")

        result = await self.db.execute(
            select(Customer).where(Customer.customerNumber == customer_id)
        )

        customer = result.scalars().first()

        if not customer:
            logger.warning(f"Update failed. Customer not found ID={customer_id}")
            return None

        update_data = data.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(customer, key, value)

        await self.db.commit()
        await self.db.refresh(customer)

        logger.info(f"Customer updated successfully ID={customer_id}")

        return customer

    async def delete_customer(self, customer_id: int):
        """
        Delete customer safely from DB.
        """

        logger.info(f"Deleting customer ID={customer_id}")

        result = await self.db.execute(
            select(Customer).where(Customer.customerNumber == customer_id)
        )

        customer = result.scalars().first()

        if not customer:
            logger.warning(f"Delete failed. Customer not found ID={customer_id}")
            return None

        await self.db.delete(customer)
        await self.db.commit()

        logger.info(f"Customer deleted ID={customer_id}")

        return customer

    async def get_customer_orders(self, customer_id: int):
        """
        Get all orders for a customer.
        """

        logger.info(f"Fetching orders for customer ID={customer_id}")

        result = await self.db.execute(
            select(Order).where(Order.customerNumber == customer_id)
        )
        orders = result.scalars().all()

        logger.info(f"Fetched {len(orders)} orders for customer ID={customer_id}")

        return orders

    async def get_customer_payments(self, customer_id: int):
        """
        Get all payments for a customer.
        """

        logger.info(f"Fetching payments for customer ID={customer_id}")

        result = await self.db.execute(
            select(Payment).where(Payment.customerNumber == customer_id)
        )
        payments = result.scalars().all()

        logger.info(f"Fetched {len(payments)} payments for customer ID={customer_id}")

        return payments
