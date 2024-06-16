from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from uuid import UUID

from src import models, schemas, auth


################################################
# USERS
################################################


def get_user_by_id(db: Session, id: int):
    return db.query(models.User).filter(models.User.id == id).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
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
# ALL SPENDINGS
################################################


def get_all_spendings_by_group_id(db: Session, group_id: int):

    unique_spendings = (
        db.query(models.UniqueSpending)
        .filter(models.UniqueSpending.group_id == group_id)
        .limit(100)
        .all()
    )
    installment_spendings = (
        db.query(models.InstallmentSpending)
        .filter(models.InstallmentSpending.group_id == group_id)
        .limit(100)
        .all()
    )
    recurring_spendings = (
        db.query(models.RecurringSpending)
        .filter(models.RecurringSpending.group_id == group_id)
        .limit(100)
        .all()
    )

    unique_spendings = list(
        map(
            lambda spending: {**spending.__dict__, "type": "unique_spending"},
            unique_spendings,
        )
    )
    installment_spendings = list(
        map(
            lambda spending: {**spending.__dict__, "type": "installment_spending"},
            installment_spendings,
        )
    )
    recurring_spendings = list(
        map(
            lambda spending: {**spending.__dict__, "type": "recurring_spending"},
            recurring_spendings,
        )
    )

    return unique_spendings + installment_spendings + recurring_spendings


################################################
# UNIQUE SPENDINGS
################################################

def create_unique_spending(db: Session, spending: schemas.UniqueSpendingCreate, user_id: int, category: models.Strategy):
    db_spending = models.UniqueSpending(owner_id=user_id, **dict(spending))
    db_spending.strategy_data = None
    db.add(db_spending)
    db.commit()
    db.refresh(db_spending)
    update_balances_from_spending(db, db_spending, category, spending.strategy_data)
    db.refresh(db_spending)
    return db_spending


def get_unique_spendings_by_group_id(db: Session, group_id: int):
    return (
        db.query(models.UniqueSpending)
        .filter(models.UniqueSpending.group_id == group_id)
        .limit(100)
        .all()
    )


################################################
# INSTALLMENT SPENDINGS
################################################


def create_installment_spending(
    db: Session,
    spending: schemas.InstallmentSpendingCreate,
    user_id: int,
    current_installment: int,
):
    db_spending = models.InstallmentSpending(
        owner_id=user_id, current_installment=current_installment, **dict(spending)
    )
    db.add(db_spending)
    db.commit()
    db.refresh(db_spending)
    update_balances_from_spending(db, db_spending)
    db.refresh(db_spending)
    return db_spending


def get_installment_spendings_by_group_id(db: Session, group_id: int):
    return (
        db.query(models.InstallmentSpending)
        .filter(models.InstallmentSpending.group_id == group_id)
        .limit(100)
        .all()
    )


################################################
# RECURRING SPENDINGS
################################################


def create_recurring_spending(
    db: Session, spending: schemas.RecurringSpendingBase, user_id: int
):
    db_spending = models.RecurringSpending(owner_id=user_id, **dict(spending))
    db.add(db_spending)
    db.commit()
    db.refresh(db_spending)
    update_balances_from_spending(db, db_spending)
    db.refresh(db_spending)
    return db_spending


def get_recurring_spendings_by_id(db: Session, recurring_spendig_id: int):
    return (
        db.query(models.RecurringSpending)
        .filter(models.RecurringSpending.id == recurring_spendig_id)
        .first()
    )


def get_recurring_spendings_by_group_id(db: Session, group_id: int):
    return (
        db.query(models.RecurringSpending)
        .filter(models.RecurringSpending.group_id == group_id)
        .limit(100)
        .all()
    )


def put_recurring_spendings(
    db: Session,
    db_recurring_spending: models.RecurringSpending,
    put_recurring_spending: schemas.RecurringSpendingPut,
):
    db_recurring_spending.amount = put_recurring_spending.amount
    db_recurring_spending.description = put_recurring_spending.description
    db_recurring_spending.category_id = put_recurring_spending.categiry_id
    db.commit()
    db.refresh(db_recurring_spending)
    return db_recurring_spending


################################################
# PAYMENTS
################################################


def create_payment(db: Session, payment: schemas.PaymentCreate):
    db_payment = models.Payment(**dict(payment))
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment


def get_payment_by_id(db: Session, payment_id: int):
    return db.query(models.Payment).filter(models.Payment.id == payment_id).first()


def get_payments_by_group_id(db: Session, group_id: int):
    return (
        db.query(models.Payment)
        .filter(models.Payment.group_id == group_id)
        .limit(100)
        .all()
    )


def confirm_payment(db: Session, db_payment: models.Payment):
    db_payment.confirmed = True
    update_balances_from_payment(db, db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment


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
# REMINDERS
################################################

def create_payment_reminder(
    db: Session, payment_reminder: schemas.PaymentReminderCreate, sender_id: int
):
    db_reminder = models.PaymentReminder(
        sender_id=sender_id,
        receiver_id=payment_reminder.receiver_id,
        group_id=payment_reminder.group_id,
    )

    if payment_reminder.message is not None:
        db_reminder.message = payment_reminder.message

    db.add(db_reminder)
    db.commit()
    db.refresh(db_reminder)
    return db_reminder


################################################
# BALANCES
################################################

def update_balances_equals(db, spending, members, balances):
    amount_per_member = spending.amount / len(members)
    for user, balance in zip(members, balances):
        amount = -amount_per_member

        if spending.owner_id == user.id:
            amount += spending.amount

        balance.current_balance += amount

def update_balances_percentage(db, spending, members, balances, strategy_data):
    for user, balance in zip(members, balances):

        amount_per_member = sum([data['value'] if data['user_id'] == user.id else 0 for data in strategy_data])
        amount_per_member = spending.amount * (amount_per_member / 100)
        amount = spending.amount - amount_per_member if spending.owner_id == user.id else -amount_per_member
        balance.current_balance += amount
    db.commit()


def update_balances_custom(db, spending, members, balances, strategy_data):
    for user, balance in zip(members, balances):
        amount_per_member = sum([data['value'] if data['user_id'] == user.id else 0 for data in strategy_data])
        amount = spending.amount - amount_per_member if spending.owner_id == user.id else -amount_per_member
        balance.current_balance += amount
    db.commit()

def update_balances_from_spending(db: Session, spending: models.UniqueSpending, strategy: models.Strategy, strategy_data):
    group = get_group_by_id(db, spending.group_id)
    balances = sorted(
        get_balances_by_group_id(db, spending.group_id), key=lambda x: x.user_id
    )
    members = sorted(group.members, key=lambda x: x.id)
    # TODO: implement division strategy
    # TODO: this truncates decimals
    # TODO: Refactor to POO
    if strategy == models.Strategy.EQUALPARTS:
        update_balances_equals(db, spending, members, balances)
    elif strategy == models.Strategy.PERCENTAGE:
        update_balances_percentage(db, spending, members, balances, strategy_data)
    elif strategy == models.Strategy.CUSTOM:
        update_balances_custom(db, spending, members, balances, strategy_data)
    
    db.commit()

################################################
# BALANCES
################################################
def update_balances_from_payment(db: Session, payment: models.Payment):
    balances = get_balances_by_group_id(db, payment.group_id)

    # Update payer balance
    payer = get_user_by_id(db, payment.from_id)
    payer_balance = next(filter(lambda x: x.user_id == payer.id, balances))
    payer_balance.current_balance += payment.amount

    # Update payee balance
    payee = get_user_by_id(db, payment.to_id)
    payee_balance = next(filter(lambda x: x.user_id == payee.id, balances))
    payee_balance.current_balance -= payment.amount

    db.commit()


def get_balances_by_group_id(db: Session, group_id: int) -> List[models.Balance]:
    return (
        db.query(models.Balance)
        .filter(models.Balance.group_id == group_id)
        .limit(100)
        .all()
    )
