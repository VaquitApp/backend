from http import HTTPStatus
from typing import Annotated
from uuid import uuid4
from fastapi import Depends, FastAPI, HTTPException, Header

from src import crud, models, schemas, auth
from src.mail import mail_service
from src.database import SessionLocal, engine
from sqlalchemy.orm import Session
import hashlib

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


def ensure_user(x_user: Annotated[str, Header()]) -> models.User:
    jwt_claims = auth.parse_jwt(x_user)
    if jwt_claims is None:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail="Necesita loguearse para continuar",
        )
    user = models.User(id=jwt_claims["id"], email=jwt_claims["email"])
    return user


app = FastAPI(dependencies=[Depends(get_db)])

UserDependency = Annotated[models.User, Depends(ensure_user)]
MailDependency = Annotated[models.Invite, Depends(get_mail_sender)]

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
            status_code=HTTPStatus.UNAUTHORIZED, detail="Contraseña incorrecta"
        )

    credentials = auth.login_user(db_user)
    return credentials


################################################
# CATEGORIES
################################################


@app.post("/category", status_code=HTTPStatus.CREATED)
def create_category(category: schemas.CategoryCreate, db: DbDependency):
    group = crud.get_group_by_id(db, category.group_id)
    if group is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Grupo inexistente"
        )
    return crud.create_category(db, category)


@app.get("/category/{group_id}")
def list_group_categories(db: DbDependency, group_id: int):
    group = crud.get_group_by_id(db, group_id)

    if group is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Grupo inexistente"
        )

    categories = crud.get_categories_by_group_id(db, group_id)

    return categories


################################################
# GROUPS
################################################


def user_id_in_group(user_id: int, group: models.Group) -> bool:
    return any(member.id == user_id for member in group.members)


def check_group_exists_and_user_is_member(user_id: int, group: models.Group):
    # If group does not exist or user is not in group
    if group is None or not user_id_in_group(user_id, group):
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Grupo inexistente"
        )


def check_group_exists_and_user_is_owner(user_id: int, group: models.Group):
    # If group does not exist or user is not in group
    if group is None or (
        group.owner_id != user_id and not user_id_in_group(user_id, group)
    ):
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Grupo inexistente"
        )

    # If user is in group, but is not the owner
    if group.owner_id != user_id:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
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

    check_group_exists_and_user_is_owner(user.id, group_to_update)

    return crud.update_group(db, group_to_update, put_group)


@app.get("/group")
def list_groups(db: DbDependency, user: UserDependency):
    return crud.get_groups_by_user_id(db, user.id)


@app.get("/group/{group_id}")
def get_group_by_id(db: DbDependency, user: UserDependency, group_id: int):
    group = crud.get_group_by_id(db, group_id)

    check_group_exists_and_user_is_member(user.id, group)

    return group


@app.post("/group/{group_id}/member", status_code=HTTPStatus.CREATED)
def add_user_to_group(
    db: DbDependency,
    user: UserDependency,
    group_id: int,
    req: schemas.AddUserToGroupRequest,
):
    group = crud.get_group_by_id(db, group_id)

    check_group_exists_and_user_is_owner(user.id, group)

    crud.add_user_to_group(db, group, req.user_id)

    return group.members


@app.get("/group/{group_id}/member")
def list_group_members(db: DbDependency, user: UserDependency, group_id: int):
    group = crud.get_group_by_id(db, group_id)

    check_group_exists_and_user_is_member(user.id, group)

    return group.members


# TODO: CUANDO TERMINEN IMPLEMENTAR EL INVITE Y JOIN, NO DEJEN INVITAR NI ACEPTAR NI NADA SI EL GRUPO ESTA ARCHIVADO.


@app.put("/group/{group_id}/archive", status_code=HTTPStatus.OK)
def archive_group(db: DbDependency, user: UserDependency, group_id: int):
    group = crud.get_group_by_id(db, group_id)

    check_group_exists_and_user_is_owner(user.id, group)

    archived_group = crud.update_group_status(db, group, True)
    return {"detail": f"Grupo {archived_group.name} archivado correctamente"}


@app.put("/group/{group_id}/unarchive", status_code=HTTPStatus.OK)
def unarchive_group(db: DbDependency, user: UserDependency, group_id: int):
    group = crud.get_group_by_id(db, group_id)

    check_group_exists_and_user_is_owner(user.id, group)

    archived_group = crud.update_group_status(db, group, False)
    return {"detail": f"Grupo {archived_group.name} desarchivado correctamente"}


################################################
# SPENDINGS
################################################


@app.post("/spending", status_code=HTTPStatus.CREATED)
def create_spending(
    spending: schemas.SpendingCreate, db: DbDependency, user: UserDependency
):
    group = crud.get_group_by_id(db, spending.group_id)

    check_group_exists_and_user_is_member(user.id, group)

    if group.is_archived:
        raise HTTPException(
            status_code=HTTPStatus.NOT_ACCEPTABLE,
            detail="El grupo esta archivado, no se pueden seguir agregando gastos.",
        )

    return crud.create_spending(db, spending, user.id)


@app.get("/spending")
def list_spendings(db: DbDependency, user: UserDependency, group_id: int):
    group = crud.get_group_by_id(db, group_id)

    check_group_exists_and_user_is_member(user.id, group)

    return crud.get_spendings_by_group_id(db, group_id)


@app.get("/group/{group_id}/spending")
def list_group_spendings(db: DbDependency, user: UserDependency, group_id: int):
    group = crud.get_group_by_id(db, group_id)

    check_group_exists_and_user_is_member(user.id, group)

    return crud.get_spendings_by_group_id(db, group_id)


################################################
# BUDGETS
################################################


@app.post("/budget", status_code=HTTPStatus.CREATED)
def create_budget(
    spending: schemas.BudgetCreate, db: DbDependency, user: UserDependency
):
    group = crud.get_group_by_id(db, spending.group_id)

    check_group_exists_and_user_is_owner(user.id, group)

    if group.is_archived:
        raise HTTPException(
            status_code=HTTPStatus.NOT_ACCEPTABLE,
            detail="El grupo esta archivado, no se pueden seguir agregando presupuestos.",
        )
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

    check_group_exists_and_user_is_member(user.id, group)

    if group.is_archived:
        raise HTTPException(
            status_code=HTTPStatus.NOT_ACCEPTABLE,
            detail="El grupo esta archivado, no se pueden seguir agregando presupuestos.",
        )
    return crud.put_budget(db, db_budget, put_budget)


@app.get("/group/{group_id}/budget")
def list_group_budgets(db: DbDependency, user: UserDependency, group_id: int):
    group = crud.get_group_by_id(db, group_id)

    check_group_exists_and_user_is_member(user.id, group)

    return crud.get_budgets_by_group_id(db, group_id)


################################################
# INVITES
################################################


@app.get("/invite/{invite_id}")
def get_invite(db: DbDependency, invite_id: int):
    invite = crud.get_invite_by_id(db, invite_id)
    if not invite:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Invitación no existente."
        )
    return invite


@app.post("/invite", status_code=HTTPStatus.CREATED)
def invite_user(
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
    if target_group is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Grupo inexistente."
        )
    elif target_group.owner_id != user.id:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail=f"El usuario {user.id} no cuenta con privilegios de invitación en el grupo {target_group.id}.",
        )

    # TODO: Check if user already has pending invite to receiver.

    token = uuid4()
    sent_ok = mail.send(
        sender=user.email, receiver=receiver.email, group=target_group, token=token.hex
    )

    if sent_ok:
        return crud.create_invite(db, user.id, token, invite)
    else:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Failed to invite user."
        )
