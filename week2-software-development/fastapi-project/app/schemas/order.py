from pydantic import BaseModel
from typing import Optional
from datetime import date


class OrderBase(BaseModel):
    """
    Base schema (shared fields).
    """

    orderDate: date
    requiredDate: date
    shippedDate: Optional[date] = None
    status: str
    comments: Optional[str] = None


class OrderResponse(OrderBase):
    """
    Response schema returned to client.
    """

    orderNumber: int
    customerNumber: int

    class Config:
        from_attributes = True
