
from sqlalchemy import Column, String, Integer, Numeric, ForeignKey
from app.db.base import Base


class Product(Base):
    __tablename__ = "products"

    productCode = Column(String(15), primary_key=True, index=True)
    productName = Column(String(70), nullable=False)
    productLine = Column(String(50), ForeignKey("productlines.productLine"))
    productScale = Column(String(10))
    productVendor = Column(String(50))
    productDescription = Column(String)
    quantityInStock = Column(Integer)
    buyPrice = Column(Numeric(10, 2))
    MSRP = Column(Numeric(10, 2))