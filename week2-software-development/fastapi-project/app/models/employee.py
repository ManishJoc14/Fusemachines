from sqlalchemy import Column, Integer, String, ForeignKey
from app.db.base import Base


class Employee(Base):
    __tablename__ = "employees"

    employeeNumber = Column(Integer, primary_key=True, index=True)
    lastName = Column(String(50))
    firstName = Column(String(50))
    extension = Column(String(10))
    email = Column(String(100))
    officeCode = Column(String(10), ForeignKey("offices.officeCode"))
    reportsTo = Column(Integer, ForeignKey("employees.employeeNumber"))
    jobTitle = Column(String(50))
