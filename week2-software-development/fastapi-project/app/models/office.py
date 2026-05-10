from sqlalchemy import Column, String
from app.db.base import Base


class Office(Base):
    __tablename__ = "offices"

    officeCode = Column(String(10), primary_key=True, index=True)
    city = Column(String(50))
    phone = Column(String(50))
    addressLine1 = Column(String(50))
    addressLine2 = Column(String(50))
    state = Column(String(50))
    country = Column(String(50))
    postalCode = Column(String(15))
    territory = Column(String(10))
