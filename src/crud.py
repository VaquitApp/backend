from sqlalchemy.orm import Session
from . import models, schemas
import hashlib


################################################
# USERS
################################################


def get_user_by_id(db: Session, id: int):
    return db.query(models.User).filter(models.User.id == id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = hashlib.sha256(user.password.encode(encoding="utf-8")).hexdigest()
    db_user = models.User(email=user.email, password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


################################################
# GROUPS
################################################


def create_group(db: Session, group: schemas.GroupCreate, user_id: int):
    db_group = models.Group(
        owner_id=user_id, name=group.name, description=group.description
    )
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group


def get_groups_by_owner_id(db: Session, owner_id: int):
    return (
        db.query(models.Group)
        .filter(models.Group.owner_id == owner_id)
        .limit(100)
        .all()
    )


################################################
# SPENDINGS
################################################


def create_spending(db: Session, spending: schemas.SpendingCreate, user_id: int):
    db_spending = models.Spending(owner_id=user_id, **dict(spending))
    db.add(db_spending)
    db.commit()
    db.refresh(db_spending)
    return db_spending


def get_spendings_by_owner_id(db: Session, owner_id: int):
    return (
        db.query(models.Spending)
        .filter(models.Spending.owner_id == owner_id)
        .limit(100)
        .all()
    )
