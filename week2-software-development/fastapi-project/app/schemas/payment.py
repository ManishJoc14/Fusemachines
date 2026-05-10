from pydantic import BaseModel
from typing import Optional
from datetime import date


class PaymentBase(BaseModel):
    """
    Base schema (shared fields).
    """

    paymentDate: date
    amount: float


class PaymentResponse(PaymentBase):
    """
    Response schema returned to client.
    """

    checkNumber: str
    customerNumber: int

    class Config:
        from_attributes = True
