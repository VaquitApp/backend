from http import HTTPStatus
from typing import Annotated, Optional
from uuid import uuid4
from fastapi import Depends, FastAPI, HTTPException, Header

from src import crud, models, schemas, auth
from src.mail import MailSender, mail_service, is_expired_invite
from src.database import SessionLocal, engine
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

models.Base.metadata.create_all(bind=engine)


def get_mail_sender():
    return mail_service


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbDependency = Annotated[Session, Depends(get_db)]


def ensure_user(db: DbDependency, x_user: Annotated[str, Header()]) -> models.User:
    jwt_claims = auth.parse_jwt(x_user)
    if jwt_claims is None:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail="Necesita loguearse para continuar",
        )
    user = crud.get_user_by_id(db, jwt_claims["id"])
    if user is None:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="Usuario no encontrado",
        )
    return user


app = FastAPI(dependencies=[Depends(get_db)])

UserDependency = Annotated[models.User, Depends(ensure_user)]
MailDependency = Annotated[MailSender, Depends(get_mail_sender)]

################################################
# USERS
################################################


@app.post("/user/register", status_code=HTTPStatus.CREATED)
def create_user(user: schemas.UserCreate, db: DbDependency) -> schemas.UserCredentials:
    db_user = crud.get_user_by_email(db, email=user.email)

    if db_user is not None:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Email ya existente"
        )

    db_user = crud.create_user(db, user)
    credentials = auth.login_user(db_user)
    return credentials


@app.post("/user/login", status_code=HTTPStatus.CREATED)
def login(user: schemas.UserLogin, db: DbDependency) -> schemas.UserCredentials:
    db_user = crud.get_user_by_email(db, email=user.email)

    if db_user is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Usuario no existe"
        )

    if not auth.valid_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Contraseña incorrecta"
        )

    credentials = auth.login_user(db_user)
    return credentials


################################################
# GROUPS
################################################


def check_group_is_unarchived(group: models.Group):
    if group.is_archived:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="El grupo esta archivado, no se pueden realizar modificaciones",
        )


def user_id_in_group(db: Session, user_id: int, group: models.Group) -> bool:
    members = crud.get_active_members(db, group)
    return any(member.id == user_id for member in members)


def check_group_exists_and_user_is_member(
    db: Session, user_id: int, group: models.Group
):
    # If group does not exist or user is not in group
    if group is None or not user_id_in_group(db, user_id, group):
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Grupo inexistente"
        )


def check_group_exists_and_user_is_owner(
    db: Session, user_id: int, group: models.Group
):
    # If group does not exist or user is not in group
    if group is None or (
        group.owner_id != user_id and not user_id_in_group(db, user_id, group)
    ):
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Grupo inexistente"
        )

    # If user is in group, but is not the owner
    if group.owner_id != user_id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="No tiene permisos para modificar este grupo",
        )


@app.post("/group", status_code=HTTPStatus.CREATED)
def create_group(group: schemas.GroupCreate, db: DbDependency, user: UserDependency):
    return crud.create_group(db, group, user.id)


@app.put("/group", status_code=HTTPStatus.OK)
def update_group(
    put_group: schemas.GroupUpdate, db: DbDependency, user: UserDependency
):
    group_to_update = crud.get_group_by_id(db, put_group.id)

    check_group_exists_and_user_is_owner(db, user.id, group_to_update)
    check_group_is_unarchived(group_to_update)

    return crud.update_group(db, group_to_update, put_group)


@app.get("/group")
def list_groups(db: DbDependency, user: UserDependency):
    return crud.get_groups_by_user_id(db, user.id)


@app.get("/group/{group_id}")
def get_group_by_id(db: DbDependency, user: UserDependency, group_id: int):
    group = crud.get_group_by_id(db, group_id)

    check_group_exists_and_user_is_member(db, user.id, group)

    return group


@app.post("/group/{group_id}/member", status_code=HTTPStatus.CREATED)
def add_user_to_group(
    db: DbDependency,
    user: UserDependency,
    group_id: int,
    req: schemas.AddUserToGroupRequest,
):
    if isinstance(req.user_identifier, str):
        user_to_add = crud.get_user_by_email(db, req.user_identifier)
    else:
        user_to_add = crud.get_user_by_id(db, req.user_identifier)

    if user_to_add is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Usuario no existe"
        )

    group = crud.get_group_by_id(db, group_id)

    check_group_exists_and_user_is_owner(db, user.id, group)
    check_group_is_unarchived(group)
    if user_id_in_group(db, user_to_add.id, group):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f"El usuario ya es miembro del grupo {group.name}",
        )

    if user_to_add.id in list(m.id for m in group.members):
        crud.readd_user_to_group(db, user_to_add, group)
    else:
        group = crud.add_user_to_group(db, user_to_add, group)

    return crud.get_active_members(db, group)


@app.get("/group/{group_id}/member")
def list_group_members(db: DbDependency, user: UserDependency, group_id: int):
    group = crud.get_group_by_id(db, group_id)

    check_group_exists_and_user_is_member(db, user.id, group)

    return crud.get_active_members(db, group)


@app.delete("/group/{group_id}/member")
def kick_from_group(
    db: DbDependency, user: UserDependency, group_id: int, user_id: Optional[int] = None
):
    group = crud.get_group_by_id(db, group_id)

    if user_id is None or user_id == user.id:
        user_id = user.id
    else:
        # Check caller is owner
        check_group_exists_and_user_is_owner(db, user.id, group)

    if user_id == group.owner_id:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="El dueño del grupo no puede abandonarlo",
        )

    # Check user to kick is in the group
    check_group_exists_and_user_is_member(db, user_id, group)

    user_balance = crud.get_user_balance(db, user_id, group_id)

    # The user is a member, so the balance should exist
    assert user_balance is not None

    if user_balance.current_balance != 0:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="El usuario tiene deudas pendientes",
        )

    crud.leave_group(db, user_balance)

    return {"detail": "El usuario abandonó el grupo correctamente"}


@app.put("/group/{group_id}/archive", status_code=HTTPStatus.OK)
def archive_group(db: DbDependency, user: UserDependency, group_id: int):
    group = crud.get_group_by_id(db, group_id)

    check_group_exists_and_user_is_owner(db, user.id, group)

    archived_group = crud.update_group_status(db, group, True)
    return {"detail": f"Grupo {archived_group.name} archivado correctamente"}


@app.put("/group/{group_id}/unarchive", status_code=HTTPStatus.OK)
def unarchive_group(db: DbDependency, user: UserDependency, group_id: int):
    group = crud.get_group_by_id(db, group_id)

    check_group_exists_and_user_is_owner(db, user.id, group)

    archived_group = crud.update_group_status(db, group, False)
    return {"detail": f"Grupo {archived_group.name} desarchivado correctamente"}


@app.get("/group/{group_id}/balance")
def list_group_balances(db: DbDependency, user: UserDependency, group_id: int):
    group = crud.get_group_by_id(db, group_id)
    check_group_exists_and_user_is_member(db, user.id, group)
    return crud.get_balances_by_group_id(db, group_id)


################################################
# CATEGORIES
################################################


@app.post("/category", status_code=HTTPStatus.CREATED)
def create_category(
    category: schemas.CategoryCreate,
    db: DbDependency,
    user: UserDependency,
):
    group = crud.get_group_by_id(db, category.group_id)
    check_group_exists_and_user_is_owner(db, user.id, group)
    check_group_is_unarchived(group)
    return crud.create_category(db, category)


@app.get("/category/{category_id}")
def get_category(db: DbDependency, user: UserDependency, category_id: int):
    category = crud.get_category_by_id(db, category_id)
    if category is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Categoria inexistente"
        )
    group = crud.get_group_by_id(db, category.group_id)
    check_group_exists_and_user_is_member(db, user.id, group)
    return category


@app.put("/category/{category_id}")
def update_category(
    category_update: schemas.CategoryUpdate,
    db: DbDependency,
    user: UserDependency,
    category_id: int,
):
    category = crud.get_category_by_id(db, category_id)
    if category is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Categoria inexistente"
        )
    group = crud.get_group_by_id(db, category.group_id)
    check_group_exists_and_user_is_owner(db, user.id, group)
    check_group_is_unarchived(group)
    return crud.update_category(db, category, category_update)


@app.put("/category/{category_id}/is_archived")
def update_category_status(
    new_status: schemas.CategoryStatusUpdate,
    db: DbDependency,
    user: UserDependency,
    category_id: int,
):
    category = crud.get_category_by_id(db, category_id)
    if category is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Categoria inexistente"
        )
    group = crud.get_group_by_id(db, category.group_id)
    check_group_exists_and_user_is_owner(db, user.id, group)
    check_group_is_unarchived(group)
    return crud.update_category_status(db, category, new_status.is_archived)


@app.get("/group/{group_id}/category")
def list_group_categories(db: DbDependency, user: UserDependency, group_id: int):
    group = crud.get_group_by_id(db, group_id)
    check_group_exists_and_user_is_member(db, user.id, group)
    categories = crud.get_categories_by_group_id(db, group_id)
    return categories


################################################
# ALL SPENDINGS
################################################


@app.get("/group/{group_id}/spending")
def list_group_unique_spendings(db: DbDependency, user: UserDependency, group_id: int):
    group = crud.get_group_by_id(db, group_id)

    check_group_exists_and_user_is_member(db, user.id, group)

    return crud.get_all_spendings_by_group_id(db, group_id)


################################################
# UNIQUE SPENDINGS
################################################


@app.post("/unique-spending", status_code=HTTPStatus.CREATED)
def create_unique_spending(
    spending: schemas.UniqueSpendingCreate, db: DbDependency, user: UserDependency
):
    group = crud.get_group_by_id(db, spending.group_id)

    check_group_exists_and_user_is_member(db, user.id, group)
    check_group_is_unarchived(group)

    category = crud.get_category_by_id(db, spending.category_id)
    if category is None or category.group_id != spending.group_id:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Categoria inexistente"
        )

    return crud.create_unique_spending(db, spending, user.id)


@app.get("/group/{group_id}/unique-spending")
def list_group_unique_spendings(db: DbDependency, user: UserDependency, group_id: int):
    group = crud.get_group_by_id(db, group_id)

    check_group_exists_and_user_is_member(db, user.id, group)

    return crud.get_unique_spendings_by_group_id(db, group_id)


################################################
# INSTALLMENT SPENDINGS
################################################


@app.post("/installment-spending", status_code=HTTPStatus.CREATED)
def create_installment_spending(
    spending: schemas.InstallmentSpendingCreate, db: DbDependency, user: UserDependency
):
    group = crud.get_group_by_id(db, spending.group_id)

    check_group_exists_and_user_is_member(db, user.id, group)
    check_group_is_unarchived(group)

    category = crud.get_category_by_id(db, spending.category_id)
    if category is None or category.group_id != spending.group_id:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Categoria inexistente"
        )

    res = []

    spending_description = spending.description
    amount_of_installments = spending.amount_of_installments
    spending_date = spending.date
    for i in range(amount_of_installments):
        spending.description = (
            f"{spending_description} | cuota {i+1}/{amount_of_installments}"
        )
        spending.date = spending_date + timedelta(days=(30 * i))
        res.append(crud.create_installment_spending(db, spending, user.id, i + 1))

    return res


@app.get("/group/{group_id}/installment-spending")
def list_group_installment_spendings(
    db: DbDependency, user: UserDependency, group_id: int
):
    group = crud.get_group_by_id(db, group_id)

    check_group_exists_and_user_is_member(db, user.id, group)

    return crud.get_installment_spendings_by_group_id(db, group_id)


################################################
# RECURRING SPENDINGS
################################################


@app.post("/recurring-spending", status_code=HTTPStatus.CREATED)
def create_recurring_spending(
    spending: schemas.RecurringSpendingCreate, db: DbDependency, user: UserDependency
):
    group = crud.get_group_by_id(db, spending.group_id)

    check_group_exists_and_user_is_member(db, user.id, group)
    check_group_is_unarchived(group)

    category = crud.get_category_by_id(db, spending.category_id)
    if category is None or category.group_id != spending.group_id:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Categoria inexistente"
        )

    return crud.create_recurring_spending(db, spending, user.id)


@app.get("/group/{group_id}/recurring-spending")
def list_group_recurring_spendings(
    db: DbDependency, user: UserDependency, group_id: int
):
    group = crud.get_group_by_id(db, group_id)

    check_group_exists_and_user_is_member(db, user.id, group)

    return crud.get_recurring_spendings_by_group_id(db, group_id)


@app.put("/recurring-spending/{recurring_spending_id}")
def put_recurring_spendings(
    db: DbDependency,
    user: UserDependency,
    recurring_spending_id: int,
    put_recurring_spending: schemas.RecurringSpendingPut,
):

    db_recurring_spending = crud.get_recurring_spendings_by_id(
        db, recurring_spending_id
    )

    if db_recurring_spending is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Gasto recurrente inexistente"
        )

    group = crud.get_group_by_id(db, db_recurring_spending.group_id)

    check_group_exists_and_user_is_member(db, user.id, group)
    check_group_is_unarchived(group)

    return crud.put_recurring_spendings(
        db, db_recurring_spending, put_recurring_spending
    )


################################################
# PAYMENTS
################################################


@app.post("/payment", status_code=HTTPStatus.CREATED)
def create_payment(
    payment: schemas.PaymentCreate, db: DbDependency, user: UserDependency
):
    group = crud.get_group_by_id(db, payment.group_id)

    # Check creator, sender, and receiver are members of the group
    check_group_exists_and_user_is_member(db, user.id, group)
    check_group_exists_and_user_is_member(db, payment.from_id, group)
    check_group_exists_and_user_is_member(db, payment.to_id, group)

    if payment.from_id == payment.to_id:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="No se puede realizar un pago a uno mismo.",
        )

    if group.is_archived:
        raise HTTPException(
            status_code=HTTPStatus.NOT_ACCEPTABLE,
            detail="El grupo esta archivado, no se pueden seguir agregando pagos.",
        )

    return crud.create_payment(db, payment)


@app.post("/payment/{payment_id}/confirm", status_code=HTTPStatus.OK)
def confirm_payment(db: DbDependency, user: UserDependency, payment_id: int):

    payment = crud.get_payment_by_id(db, payment_id)
    if payment is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"No se consiguió el pago.",
        )

    if payment.confirmed:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f"Este pago ya fue confirmado.",
        )

    if payment.to_id != user.id:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f"Solo el receptor del pago puede confirmarlo.",
        )

    return crud.confirm_payment(db, payment)


@app.get("/payment")
def list_payments(db: DbDependency, user: UserDependency, group_id: int):
    group = crud.get_group_by_id(db, group_id)

    check_group_exists_and_user_is_member(db, user.id, group)

    return crud.get_payments_by_group_id(db, group_id)


@app.get("/group/{group_id}/payment")
def list_group_payments(db: DbDependency, user: UserDependency, group_id: int):
    group = crud.get_group_by_id(db, group_id)

    check_group_exists_and_user_is_member(db, user.id, group)

    return crud.get_payments_by_group_id(db, group_id)


################################################
# BUDGETS
################################################


@app.post("/budget", status_code=HTTPStatus.CREATED)
def create_budget(
    spending: schemas.BudgetCreate, db: DbDependency, user: UserDependency
):
    group = crud.get_group_by_id(db, spending.group_id)

    check_group_exists_and_user_is_owner(db, user.id, group)
    check_group_is_unarchived(group)

    return crud.create_budget(db, spending)


@app.get("/budget/{budget_id}")
def get_budget(db: DbDependency, user: UserDependency, budget_id: int):
    return crud.get_budget_by_id(db, budget_id)


@app.put("/budget/{budget_id}")
def put_budget(
    db: DbDependency,
    user: UserDependency,
    budget_id: int,
    put_budget: schemas.BudgetPut,
):

    db_budget = crud.get_budget_by_id(db, budget_id)

    if db_budget is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Presupuesto inexistente"
        )

    group = crud.get_group_by_id(db, db_budget.group_id)

    check_group_exists_and_user_is_member(db, user.id, group)
    check_group_is_unarchived(group)

    return crud.put_budget(db, db_budget, put_budget)


@app.get("/group/{group_id}/budget")
def list_group_budgets(db: DbDependency, user: UserDependency, group_id: int):
    group = crud.get_group_by_id(db, group_id)

    check_group_exists_and_user_is_member(db, user.id, group)

    return crud.get_budgets_by_group_id(db, group_id)


################################################
# INVITES
################################################


@app.get("/invite/{token}")
def get_invite(db: DbDependency, token: str):
    invite = crud.get_invite_by_token(db, token)
    if not invite:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Invitación no existente."
        )
    return invite


@app.post("/invite", status_code=HTTPStatus.CREATED)
def send_invite(
    db: DbDependency,
    user: UserDependency,
    mail: MailDependency,
    invite: schemas.InviteCreate,
):
    receiver = crud.get_user_by_email(db, invite.receiver_email)
    if receiver is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="El Usuario a invitar no esta registrado en VaquitApp.",
        )
    invite.receiver_id = receiver.id

    target_group = crud.get_group_by_id(db, invite.group_id)
    check_group_exists_and_user_is_owner(db, user.id, target_group)
    check_group_is_unarchived(target_group)

    if user_id_in_group(db, receiver.id, target_group):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f"El usuario ya es miembro del grupo {target_group.name}",
        )

    token = uuid4()
    sent_ok = mail.send_invite(
        sender=user.email, receiver=receiver.email, group=target_group, token=token.hex
    )

    if sent_ok:
        return crud.create_invite(db, user.id, token, invite)
    else:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="No se pudo invitar al usuario."
        )


@app.post("/invite/join/{invite_token}", status_code=HTTPStatus.OK)
def accept_invite(db: DbDependency, user: UserDependency, invite_token: str):
    target_invite = crud.get_invite_by_token(db, invite_token)
    if target_invite is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"No existe invitacion con el token: {invite_token}",
        )

    if is_expired_invite(target_invite.creation_date):
        if target_invite.status == schemas.InviteStatus.PENDING:
            crud.update_invite_status(db, target_invite, schemas.InviteStatus.EXPIRED)
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail="La invitacion ha expirado.",
        )

    if user.id != target_invite.receiver_id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="La invitacion no es para este usuario!",
        )

    target_group = crud.get_group_by_id(db, target_invite.group_id)
    if target_group is None or target_group.is_archived:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="No se puede agregar un nuevo miembro a este grupo.",
        )

    if user_id_in_group(db, user.id, target_group):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f"El usuario ya es miembro del grupo {target_group.name}",
        )

    if user.id in list(m.id for m in target_group.members):
        crud.readd_user_to_group(db, user, target_group)
    else:
        crud.add_user_to_group(db, user, target_group)

    return crud.update_invite_status(db, target_invite, schemas.InviteStatus.ACCEPTED)


################################################
# REMINDERS
################################################


@app.post("/payment_reminder", status_code=HTTPStatus.CREATED)
def send_payment_reminder(
    db: DbDependency,
    user: UserDependency,
    mail: MailDependency,
    payment_reminder: schemas.PaymentReminderCreate,
):

    receiver = crud.get_user_by_email(db, payment_reminder.receiver_email)
    if receiver is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="No se encontro el usuario receptor.",
        )
    group = crud.get_group_by_id(db, payment_reminder.group_id)
    check_group_exists_and_user_is_member(db, receiver.id, group)
    check_group_is_unarchived(group)
    payment_reminder.receiver_id = receiver.id

    sent_ok = mail.send_reminder(
        sender=user.email,
        receiver=receiver.email,
        group=group,
        message=payment_reminder.message,
    )

    if sent_ok:
        return crud.create_payment_reminder(db, payment_reminder, user.id)
    else:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="No se pudo enviar recordatorio de pago al usuario.",
        )
