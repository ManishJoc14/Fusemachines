from pydantic import BaseModel
from typing import Optional


class CustomerBase(BaseModel):
    """
    Shared fields for Customer.
    Used as a base for Create and Response schemas.
    """

    customerName: str
    contactFirstName: str
    contactLastName: str
    phone: str

    addressLine1: str
    addressLine2: Optional[str] = None

    city: str
    state: Optional[str] = None
    postalCode: Optional[str] = None
    country: str

    creditLimit: Optional[float] = None

    salesRepEmployeeNumber: Optional[int] = None


# Input for POST
class CustomerCreate(CustomerBase):
    """
    Used when creating a new customer.
    Inherits all fields from CustomerBase.
    """

    pass


# Input for PATCH
class CustomerUpdate(BaseModel):
    """
    Partial update schema.
    All fields are optional for PATCH requests.
    """

    customerName: Optional[str] = None
    contactFirstName: Optional[str] = None
    contactLastName: Optional[str] = None
    phone: Optional[str] = None

    addressLine1: Optional[str] = None
    addressLine2: Optional[str] = None

    city: Optional[str] = None
    state: Optional[str] = None
    postalCode: Optional[str] = None
    country: Optional[str] = None

    salesRepEmployeeNumber: Optional[int] = None
    creditLimit: Optional[float] = None


# Output for GET
class CustomerResponse(CustomerBase):
    """
    What API returns to client.
    Includes primary key.
    """

    customerNumber: int

    class Config:
        from_attributes = True


# Outpur for DELETE
class CustomerDeleteResponse(BaseModel):
    """
    Response schema for customer deletion.
    """

    message: str
