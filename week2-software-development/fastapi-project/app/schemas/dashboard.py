from pydantic import BaseModel


class CountResponse(BaseModel):
    """
    Reusable schema for count endpoints.
    """

    count: int


class OverallCountsResponse(BaseModel):
    """
    Response schema for overall dashboard counts.
    """

    customers: int
    orders: int
    products: int
    employees: int
    offices: int
    payments: int
    orderdetails: int
    productlines: int