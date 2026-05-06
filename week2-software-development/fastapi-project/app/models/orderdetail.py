from sqlalchemy import Column, Integer, String, Numeric, SmallInteger, ForeignKey
from app.db.base import Base


class OrderDetail(Base):
    __tablename__ = "orderdetails"

    orderNumber = Column(Integer, ForeignKey("orders.orderNumber"), primary_key=True)
    productCode = Column(String(15), ForeignKey("products.productCode"), primary_key=True)
    quantityOrdered = Column(Integer)
    priceEach = Column(Numeric(10, 2))
    orderLineNumber = Column(SmallInteger)