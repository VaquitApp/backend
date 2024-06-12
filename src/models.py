from datetime import datetime
from typing import Set
from uuid import uuid4
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Boolean,
    UniqueConstraint,
    func,
    Enum,
    UUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.schemas import InviteStatus
from src.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    groups: Mapped[Set["Group"]] = relationship(
        secondary="balances", back_populates="members"
    )


class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True)
    owner_id = Column(ForeignKey("users.id"))
    name = Column(String)
    description = Column(String)
    is_archived = Column(Boolean)
    members: Mapped[Set[User]] = relationship(
        secondary="balances", back_populates="groups"
    )


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    group_id = Column(ForeignKey("groups.id"))
    name = Column(String)
    description = Column(String)
    # TODO: move strategy to enums
    strategy = Column(String)

    __table_args__ = (UniqueConstraint("group_id", "name"),)


class Spending(Base):
    __tablename__ = "spendings"

    id = Column(Integer, primary_key=True)
    owner_id = Column(ForeignKey("users.id"))
    group_id = Column(ForeignKey("groups.id"))
    category_id = Column(ForeignKey("categories.id"))
    amount = Column(Integer)
    description = Column(String)
    date: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True)
    group_id = Column(ForeignKey("groups.id"))
    category_id = Column(ForeignKey("categories.id"))
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
    token = Column(UUID(as_uuid=True), unique=True, default=uuid4)
    status = Column(Enum(InviteStatus))
    creation_date: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    spending_id = Column(ForeignKey("spendings.id"))
    from_user_id = Column(ForeignKey("users.id"))
    to_user_id = Column(ForeignKey("users.id"))
    date: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    amount = Column(Integer)

    __table_args__ = (UniqueConstraint("spending_id", "to_user_id"),)


class Balance(Base):
    __tablename__ = "balances"

    id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey("users.id"))
    group_id = Column(ForeignKey("groups.id"))
    current_balance = Column(Integer, default=0)

    __table_args__ = (UniqueConstraint("user_id", "group_id"),)

class PaymentReminder(Base):
    __tablename__ = "payment_reminders"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))
    group_id = Column(Integer, ForeignKey("groups.id"))
    message = Column(String)
    creation_date: Mapped[datetime] = mapped_column(DateTime, default=func.now())

