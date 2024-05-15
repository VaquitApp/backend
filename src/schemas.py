import datetime
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


################################################
# GROUPS
################################################


class GroupBase(BaseModel):
    name: str
    description: str


class GroupCreate(GroupBase):
    pass


class Group(GroupBase):
    id: int
    owner_id: int


################################################
# SPENDINGS
################################################


class SpendingBase(BaseModel):
    amount: int
    description: str
    date: Optional[datetime.date] = Field(None)
    group_id: int


class SpendingCreate(SpendingBase):
    pass


class Spending(SpendingBase):
    id: int
    owner_id: int
