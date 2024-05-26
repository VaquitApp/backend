from datetime import datetime
from enum import StrEnum, auto
from typing import Optional
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
    user_id: int


################################################
# CATEGORIES
################################################


class CategoryBase(BaseModel):
    name: str
    description: str
    group_id: str
    strategy: str


class CategoryCreate(CategoryBase):
    pass


class Category(CategoryBase):
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
# SPENDINGS
################################################


class SpendingBase(BaseModel):
    amount: int
    description: str
    date: Optional[datetime] = Field(None)
    group_id: int


class SpendingCreate(SpendingBase):
    pass


class Spending(SpendingBase):
    id: int
    owner_id: int


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
    group_id: int


class InviteCreate(InviteBase):
    receiver_email: str


class Invite(InviteBase):
    id: int
    sender_id: int
    status: InviteStatus
