from sqlalchemy import Column, Integer, String, Date, Numeric, ForeignKey
from app.db.base import Base


class Payment(Base):
    __tablename__ = "payments"

    customerNumber = Column(Integer, ForeignKey("customers.customerNumber"), primary_key=True)
    checkNumber = Column(String(50), primary_key=True)
    paymentDate = Column(Date)
    amount = Column(Numeric(10, 2))