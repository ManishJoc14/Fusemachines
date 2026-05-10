from sqlalchemy import Column, String, Text, LargeBinary
from app.db.base import Base


class ProductLine(Base):
    __tablename__ = "productlines"

    productLine = Column(String(50), primary_key=True, index=True)
    textDescription = Column(String(4000))
    htmlDescription = Column(Text)
    image = Column(LargeBinary)
