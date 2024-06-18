from datetime import datetime
from enum import StrEnum, auto
from typing import Optional, Union, Dict, List
from typing_extensions import TypedDict
from uuid import UUID
from pydantic import BaseModel, Field


################################################
# USERS
################################################


class UserBase(BaseModel):
    email: str


class UserLogin(UserBase):
    password: str


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int


class UserCredentials(User):
    jwt: str


class AddUserToGroupRequest(BaseModel):
    user_identifier: Union[int, str]


################################################
# CATEGORIES
################################################


class CategoryBase(BaseModel):
    name: str
    description: str
    strategy: str


class Category(CategoryBase):
    id: int
    group_id: int


class CategoryCreate(CategoryBase):
    group_id: int


class CategoryUpdate(CategoryBase):
    pass


################################################
# GROUPS
################################################


class GroupBase(BaseModel):
    name: str
    description: str


class GroupCreate(GroupBase):
    pass


class GroupUpdate(GroupCreate):
    id: int


class Group(GroupBase):
    id: int
    owner_id: int
    is_archived: bool


################################################
# STRATEGY
################################################

class Strategy(StrEnum):
    EQUALPARTS = auto()
    PERCENTAGE = auto()
    CUSTOM = auto()


class Distribution(TypedDict):
    user_id: int
    value: float


################################################
# SPENDINGS
################################################

class UniqueSpendingBase(BaseModel):
    amount: int
    description: str
    date: Optional[datetime] = Field(None)
    group_id: int
    category_id: int

class UniqueSpendingCreate(UniqueSpendingBase):
    strategy_data: Optional[List[Distribution]] = Field(None)

class UniqueSpending(UniqueSpendingBase):
    id: int
    owner_id: int


################################################
# INSTALLMENT SPENDINGS
################################################


class InstallmentSpendingBase(BaseModel):
    amount: int
    description: str
    date: Optional[datetime] = Field(None)
    group_id: int
    category_id: int
    amount_of_installments: int


class InstallmentSpendingCreate(InstallmentSpendingBase):
    strategy_data: Optional[List[Distribution]] = Field(None)


class InstallmentSpending(InstallmentSpendingBase):
    id: int
    owner_id: int
    current_installment: int


################################################
# RECURRING SPENDINGS
################################################


class RecurringSpendingBase(BaseModel):
    amount: int
    description: str
    date: Optional[datetime] = Field(None)
    group_id: int
    category_id: int


class RecurringSpendingCreate(RecurringSpendingBase):
    strategy_data: Optional[List[Distribution]] = Field(None)


class RecurringSpendingPut(RecurringSpendingBase):
    id: int
    owner_id: int


class RecurringSpending(RecurringSpendingBase):
    id: int
    owner_id: int


################################################
# PAYMENTS
################################################


class PaymentBase(BaseModel):
    group_id: int
    from_id: int
    to_id: int
    amount: int
    date: Optional[datetime] = Field(None)


class PaymentCreate(PaymentBase):
    pass


class Payment(PaymentBase):
    id: int


################################################
# BUDGETS
################################################


class BudgetBase(BaseModel):
    amount: int
    description: str
    start_date: datetime
    end_date: datetime
    category_id: int


class BudgetCreate(BudgetBase):
    group_id: int


class BudgetPut(BudgetBase):
    pass


class Budget(BudgetBase):
    id: int
    group_id: int


################################################
# INVITES
################################################


class InviteStatus(StrEnum):
    PENDING = auto()
    ACCEPTED = auto()
    EXPIRED = auto()


class InviteBase(BaseModel):
    creation_date: Optional[datetime] = Field(None)
    receiver_id: Optional[int] = Field(None)
    token: Optional[UUID] = Field(None)
    group_id: int


class InviteCreate(InviteBase):
    receiver_email: str


class Invite(InviteBase):
    id: int
    sender_id: int
    status: InviteStatus


################################################
# REMINDERS
################################################


class PaymentReminderBase(BaseModel):
    creation_date: Optional[datetime] = Field(None)
    receiver_id: Optional[int] = Field(None)
    group_id: int
    message: Optional[str] = Field(None)


class PaymentReminderCreate(PaymentReminderBase):
    receiver_email: str


class PaymentReminder(PaymentReminderBase):
    id: int
    sender_id: int
