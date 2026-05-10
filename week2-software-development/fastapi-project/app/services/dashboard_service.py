from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import logging

from app.models.customer import Customer
from app.models.order import Order
from app.models.product import Product
from app.models.employee import Employee
from app.models.office import Office
from app.models.payment import Payment
from app.models.orderdetail import OrderDetail
from app.models.productline import ProductLine

logger = logging.getLogger(__name__)


class DashboardService:
    """
    Service layer for dashboard counts.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize database session.
        """

        self.db = db

    async def count_customers(self):
        """
        Count all customers.
        """

        logger.info("Counting all customers")

        try:
            result = await self.db.execute(select(func.count()).select_from(Customer))

            count = result.scalar() or 0

            logger.info(f"Customer count query completed. Total={count}")

            return count

        except Exception as e:
            logger.error(f"Customer count query failed: {str(e)}")

            return 0

    async def count_orders(self):
        """
        Count all orders.
        """

        logger.info("Counting all orders")

        try:
            result = await self.db.execute(select(func.count()).select_from(Order))

            count = result.scalar() or 0

            logger.info(f"Order count query completed. Total={count}")

            return count

        except Exception as e:
            logger.error(f"Order count query failed: {str(e)}")

            return 0

    async def count_products(self):
        """
        Count all product.
        """

        logger.info("Counting all product")

        try:
            result = await self.db.execute(select(func.count()).select_from(Product))

            count = result.scalar() or 0

            logger.info(f"Product count query completed. Total={count}")

            return count

        except Exception as e:
            logger.error(f"Product count query failed: {str(e)}")

            return 0

    async def count_employees(self):
        """
        Count all employee.
        """

        logger.info("Counting all employee")

        try:
            result = await self.db.execute(select(func.count()).select_from(Employee))

            count = result.scalar() or 0

            logger.info(f"Employee count query completed. Total={count}")

            return count

        except Exception as e:
            logger.error(f"Employee count query failed: {str(e)}")

            return 0

    async def count_offices(self):
        """
        Count all office.
        """

        logger.info("Counting all office")

        try:
            result = await self.db.execute(select(func.count()).select_from(Office))

            count = result.scalar() or 0

            logger.info(f"Office count query completed. Total={count}")

            return count

        except Exception as e:
            logger.error(f"Office count query failed: {str(e)}")

            return 0

    async def count_payments(self):
        """
        Count all payment.
        """

        logger.info("Counting all payment")

        try:
            result = await self.db.execute(select(func.count()).select_from(Payment))

            count = result.scalar() or 0

            logger.info(f"Payment count query completed. Total={count}")

            return count

        except Exception as e:
            logger.error(f"Payment count query failed: {str(e)}")

            return 0

    async def count_order_details(self):
        """
        Count all order_detail.
        """

        logger.info("Counting all order_detail")

        try:
            result = await self.db.execute(
                select(func.count()).select_from(OrderDetail)
            )

            count = result.scalar() or 0

            logger.info(f"OrderDetail count query completed. Total={count}")

            return count

        except Exception as e:
            logger.error(f"OrderDetail count query failed: {str(e)}")

            return 0

    async def count_product_lines(self):
        """
        Count all product_line.
        """

        logger.info("Counting all product_line")

        try:
            result = await self.db.execute(
                select(func.count()).select_from(ProductLine)
            )

            count = result.scalar() or 0

            logger.info(f"ProductLine count query completed. Total={count}")

            return count

        except Exception as e:
            logger.error(f"ProductLine count query failed: {str(e)}")

            return 0
