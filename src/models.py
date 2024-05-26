from datetime import datetime
from typing import Set
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Boolean,
    Table,
    func,
    Enum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.schemas import InviteStatus
from src.database import Base


user_to_group_table = Table(
    "user_to_group_table",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("group_id", ForeignKey("groups.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    groups: Mapped[Set["Group"]] = relationship(
        secondary=user_to_group_table, back_populates="members"
    )


class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True)
    owner_id = Column(ForeignKey("users.id"))
    name = Column(String)
    description = Column(String)
    is_archived = Column(Boolean)
    members: Mapped[Set[User]] = relationship(
        secondary=user_to_group_table, back_populates="groups"
    )


class Category(Base):
    __tablename__ = "categories"

    name = Column(String, primary_key=True)
    description = Column(String)
    group_id = Column(ForeignKey("groups.id"), primary_key=True)


class Spending(Base):
    __tablename__ = "spendings"

    id = Column(Integer, primary_key=True)
    owner_id = Column(ForeignKey("users.id"))
    group_id = Column(ForeignKey("groups.id"))
    amount = Column(Integer)
    description = Column(String)
    date: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True)
    group_id = Column(ForeignKey("groups.id"))
    category_id = Column(Integer)  # TODO: Column(ForeignKey("categories.id"))
    start_date: Mapped[datetime] = mapped_column(DateTime)
    end_date: Mapped[datetime] = mapped_column(DateTime)
    amount = Column(Integer)
    description = Column(String)


class Invite(Base):
    __tablename__ = "invites"

    id = Column(Integer, primary_key=True)
    sender_id = Column(ForeignKey("users.id"))
    receiver_id = Column(ForeignKey("users.id"))
    group_id = Column(ForeignKey("groups.id"))
    status = Column(Enum(InviteStatus))
    creation_date: Mapped[datetime] = mapped_column(DateTime, default=func.now())
