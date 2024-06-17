from datetime import datetime
from typing import Set
from uuid import uuid4
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Float,
    String,
    Boolean,
    UniqueConstraint,
    func,
    Enum,
    UUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.schemas import InviteStatus, Strategy
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
    strategy = Column(Enum(Strategy))

    __table_args__ = (UniqueConstraint("group_id", "name"),)


class UniqueSpending(Base):
    __tablename__ = "unique_spendings"

    id = Column(Integer, primary_key=True)
    owner_id = Column(ForeignKey("users.id"))
    group_id = Column(ForeignKey("groups.id"))
    category_id = Column(ForeignKey("categories.id"))
    amount = Column(Integer)
    description = Column(String)
    strategy_data = Column(String)
    date: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class InstallmentSpending(Base):
    __tablename__ = "installment_spendings"

    id = Column(Integer, primary_key=True)
    owner_id = Column(ForeignKey("users.id"))
    group_id = Column(ForeignKey("groups.id"))
    category_id = Column(ForeignKey("categories.id"))
    amount = Column(Integer)
    description = Column(String)
    amount_of_installments = Column(Integer)
    current_installment = Column(Integer)
    date: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class RecurringSpending(Base):
    __tablename__ = "recurring_spendings"

    id = Column(Integer, primary_key=True)
    owner_id = Column(ForeignKey("users.id"))
    group_id = Column(ForeignKey("groups.id"))
    category_id = Column(ForeignKey("categories.id"))
    amount = Column(Float)
    description = Column(String)
    date: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    group_id = Column(ForeignKey("groups.id"))
    from_id = Column(ForeignKey("users.id"))
    to_id = Column(ForeignKey("users.id"))
    amount = Column(Integer)
    confirmed = Column(Boolean, default=False)
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


class Balance(Base):
    __tablename__ = "balances"

    id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey("users.id"))
    group_id = Column(ForeignKey("groups.id"))
    current_balance = Column(Integer, default=0)
    left = Column(Boolean, default=False)

    __table_args__ = (UniqueConstraint("user_id", "group_id"),)


class PaymentReminder(Base):
    __tablename__ = "payment_reminders"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))
    group_id = Column(Integer, ForeignKey("groups.id"))
    message = Column(String)
    creation_date: Mapped[datetime] = mapped_column(DateTime, default=func.now())
