from sqlalchemy.orm import Session
from . import models, schemas
import hashlib


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


def create_group(db: Session, group: schemas.GroupCreate, user_id: int):
    db_group = models.Group(
        owner_id=user_id, name=group.name, description=group.description
    )
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group
