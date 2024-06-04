from typing import List
from sqlalchemy import select
from sqlalchemy.orm import Session
from uuid import UUID

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
        group_id=category.group_id,
        name=category.name,
        description=category.description,
        strategy=category.strategy,
    )
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category


def get_categories_by_group_id(db: Session, group_id: int):
    return db.query(models.Category).filter(models.Category.group_id == group_id).all()


def get_category_by_id(db: Session, id: int):
    return db.query(models.Category).filter(models.Category.id == id).first()


def delete_category(db: Session, category: models.Category):
    db.delete(category)
    db.commit()
    return category


def update_category(
    db: Session, category: models.Category, category_update: schemas.CategoryUpdate
):
    category.name = category_update.name
    category.description = category_update.description
    category.strategy = category_update.strategy
    db.commit()
    db.refresh(category)
    return category


################################################
# GROUPS
################################################


def create_group(db: Session, group: schemas.GroupCreate, user_id: int):
    # Create the group
    db_group = models.Group(
        owner_id=user_id,
        name=group.name,
        description=group.description,
        is_archived=False,
    )
    db.add(db_group)

    # Add the owner to the group members
    db_user = get_user_by_id(db, user_id)

    db_group.members.add(db_user)
    db.commit()
    db.refresh(db_group)
    return db_group


def update_group(db: Session, db_group: models.Group, put_group: schemas.GroupUpdate):
    db_group.name = put_group.name
    db_group.description = put_group.description
    db.commit()
    db.refresh(db_group)
    return db_group


def get_groups_by_user_id(db: Session, user_id: int):
    return (
        db.execute(
            select(models.Group)
            .where(models.Group.members.any(models.User.id == user_id))
            .limit(100)
        )
        .scalars()
        .all()
    )


def get_group_by_id(db: Session, group_id: int):
    return db.query(models.Group).filter(models.Group.id == group_id).first()


def update_group_status(db: Session, group: models.Group, status: bool):
    group.is_archived = status
    db.commit()
    db.refresh(group)
    return group


def add_user_to_group(db: Session, user: models.User, group: models.Group):
    group.members.add(user)
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
    create_transactions_from_spending(db, db_spending)
    db.refresh(db_spending)
    return db_spending


def get_spendings_by_group_id(db: Session, group_id: int):
    return (
        db.query(models.Spending)
        .filter(models.Spending.group_id == group_id)
        .limit(100)
        .all()
    )


def get_spendings_by_category(db: Session, category_id: int):
    return (
        db.query(models.Spending)
        .filter(models.Spending.category_id == category_id)
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


################################################
# INVITES
################################################


def get_invite_by_token(db: Session, token: str):
    return db.query(models.Invite).filter(models.Invite.token == UUID(token)).first()


def create_invite(
    db: Session, sender_id: int, token: UUID, invite: schemas.InviteCreate
):
    db_invite = models.Invite(
        sender_id=sender_id,
        receiver_id=invite.receiver_id,
        group_id=invite.group_id,
        token=token,
        status=schemas.InviteStatus.PENDING,
    )
    db.add(db_invite)
    db.commit()
    db.refresh(db_invite)
    return db_invite


def update_invite_status(
    db: Session, db_invite: models.Invite, status: schemas.InviteStatus
):
    db_invite.status = status
    db.commit()
    db.refresh(db_invite)
    return db_invite


################################################
# TRANSACTIONS
################################################


def create_transactions_from_spending(db: Session, spending: models.Spending):
    group = get_group_by_id(db, spending.group_id)
    balances = sorted(
        get_balances_by_group_id(db, spending.group_id), key=lambda x: x.user_id
    )
    members = sorted(group.members, key=lambda x: x.id)
    # TODO: implement division strategy
    # TODO: this truncates decimals
    amount_per_member = spending.amount // len(members)
    txs = []
    for user, balance in zip(members, balances):
        amount = -amount_per_member

        if spending.owner_id == user.id:
            amount += spending.amount

        tx = models.Transaction(
            from_user_id=spending.owner_id,
            to_user_id=user.id,
            amount=amount,
            spending_id=spending.id,
        )
        txs.append(tx)
        db.add(tx)
        balance.current_balance += amount

    db.commit()


################################################
# BALANCES
################################################


def get_balances_by_group_id(db: Session, group_id: int) -> List[models.Balance]:
    return (
        db.query(models.Balance)
        .filter(models.Balance.group_id == group_id)
        .limit(100)
        .all()
    )
