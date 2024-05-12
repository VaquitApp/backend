from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)


class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True)
    owner_id = Column(ForeignKey("users.id"))
    name = Column(String)
    description = Column(String)


class Spending(Base):
    __tablename__ = "spendings"

    id = Column(Integer, primary_key=True)
    owner_id = Column(ForeignKey("users.id"))
    amount = Column(int)
    date: Mapped[datetime] = mapped_column(DateTime, default=func.now())
