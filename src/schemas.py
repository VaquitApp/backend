from pydantic import BaseModel


class UserBase(BaseModel):
    email: str


class UserLogin(UserBase):
    password: str


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int


class GroupBase(BaseModel):
    name: str


class GroupCreate(GroupBase):
    description: str


class Group(GroupBase):
    id: int
    owner_id: int
    description: str
