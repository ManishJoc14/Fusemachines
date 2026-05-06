from sqlalchemy import Column, Integer, String, Date, ForeignKey
from app.db.base import Base


class Order(Base):
    __tablename__ = "orders"

    orderNumber = Column(Integer, primary_key=True, index=True)
    orderDate = Column(Date)
    requiredDate = Column(Date)
    shippedDate = Column(Date)
    status = Column(String(15))
    comments = Column(String)
    customerNumber = Column(Integer, ForeignKey("customers.customerNumber"))