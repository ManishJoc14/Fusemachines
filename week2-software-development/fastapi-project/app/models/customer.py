from sqlalchemy import Column, Integer, String, Numeric, ForeignKey

from app.db.base import Base


class Customer(Base):
    """
    Customer table model.

    Represents customers in the database.
    """

    __tablename__ = "customers"

    # Primary key
    customerNumber = Column(Integer, primary_key=True, index=True)

    # Basic info
    customerName = Column(String(50), nullable=False)

    contactLastName = Column(String(50), nullable=False)
    contactFirstName = Column(String(50), nullable=False)

    phone = Column(String(50), nullable=False)

    # Address
    addressLine1 = Column(String(50), nullable=False)
    addressLine2 = Column(String(50), nullable=True)
    city = Column(String(50), nullable=False)
    state = Column(String(50), nullable=True)
    postalCode = Column(String(15), nullable=True)
    country = Column(String(50), nullable=False)

    # Financial
    creditLimit = Column(Numeric(10, 2), nullable=True)

    # Relations
    salesRepEmployeeNumber = Column(
        Integer,
        ForeignKey("employees.employeeNumber"),
        nullable=True,
    )
