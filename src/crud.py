from sqlalchemy.orm import Session
import hashlib

from src import models, schemas, auth


################################################
# USERS
################################################


def get_user_by_id(db: Session, id: int):
    return db.query(models.User).filter(models.User.id == id).first()


def get_user_by_email(db: Session, email: str) -> models.User:
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    hashed_password = auth.compute_password_hash(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


################################################
# CATEGORY
################################################


def create_category(db: Session, category: schemas.CategoryCreate):
    new_category = models.Category(
        name=category.name, description=category.description, group_id=category.group_id
    )
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category


def get_categories_by_group_id(db: Session, group_id: int):
    return db.query(models.Category).filter(models.Category.group_id == group_id).all()


################################################
# GROUPS
################################################


def create_group(db: Session, group: schemas.GroupCreate, user_id: int):
    db_group = models.Group(
        owner_id=user_id,
        name=group.name,
        description=group.description,
        is_archived=False,
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


def get_group_by_id(db: Session, group_id: int):
    return db.query(models.Group).filter(models.Group.id == group_id).first()


def update_group_status(db: Session, group: models.Group, status: bool):
    group.is_archived = status
    db.commit()
    db.refresh(group)
    return group


################################################
# SPENDINGS
################################################


def create_spending(db: Session, spending: schemas.SpendingCreate, user_id: int):
    db_spending = models.Spending(owner_id=user_id, **dict(spending))
    db.add(db_spending)
    db.commit()
    db.refresh(db_spending)
    return db_spending


def get_spendings_by_group_id(db: Session, group_id: int):
    return (
        db.query(models.Spending)
        .filter(models.Spending.group_id == group_id)
        .limit(100)
        .all()
    )


################################################
# BUDGETS
################################################


def create_budget(db: Session, budget: schemas.BudgetCreate):
    db_budget = models.Budget(**dict(budget))
    db.add(db_budget)
    db.commit()
    db.refresh(db_budget)
    return db_budget


def get_budget_by_id(db: Session, budget_id: int):
    return db.query(models.Budget).filter(models.Budget.id == budget_id).first()


def put_budget(db: Session, db_budget: models.Budget, put_budget: schemas.BudgetPut):
    db_budget.amount = put_budget.amount
    db_budget.description = put_budget.description
    db_budget.start_date = put_budget.start_date
    db_budget.end_date = put_budget.end_date
    db_budget.category_id = put_budget.category_id
    db.commit()
    db.refresh(db_budget)
    return db_budget


def get_budgets_by_group_id(db: Session, group_id: int):
    return (
        db.query(models.Budget)
        .filter(models.Budget.group_id == group_id)
        .limit(100)
        .all()
    )
