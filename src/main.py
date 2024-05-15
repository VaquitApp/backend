from http import HTTPStatus
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, Header
from . import crud, models, schemas
from .database import SessionLocal, engine
from sqlalchemy.orm import Session
import hashlib

models.Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbDependency = Annotated[Session, Depends(get_db)]


def get_user(db: DbDependency, x_user: Annotated[int, Header()]) -> models.User:
    db_user = crud.get_user_by_id(db, x_user)
    if db_user is None:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail="Necesita loguearse para continuar",
        )
    return db_user


app = FastAPI(dependencies=[Depends(get_db)])

UserDependency = Annotated[models.User, Depends(get_user)]

################################################
# USERS
################################################


@app.post("/user/register", status_code=HTTPStatus.CREATED)
def create_user(user: schemas.UserCreate, db: DbDependency):
    db_user = crud.get_user_by_email(db, email=user.email)

    if db_user is not None:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Email ya existente"
        )

    db_user = crud.create_user(db, user)

    return {"id": db_user.id}


@app.post("/user/login", status_code=HTTPStatus.CREATED)
def login(user: schemas.UserLogin, db: DbDependency):
    db_user = crud.get_user_by_email(db, email=user.email)

    if db_user is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Usuario no existe"
        )

    hashed_password = hashlib.sha256(user.password.encode(encoding="utf-8")).hexdigest()

    if db_user.password != hashed_password:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED, detail="Contraseña incorrecta"
        )

    return {"token": db_user.id}


################################################
# GROUPS
################################################


@app.post("/group", status_code=HTTPStatus.CREATED)
def create_group(group: schemas.GroupCreate, db: DbDependency, user: UserDependency):
    return crud.create_group(db, group, user.id)


@app.get("/group")
def list_groups(db: DbDependency, user: UserDependency):
    return crud.get_groups_by_owner_id(db, user.id)


@app.get("/group/{group_id}")
def list_groups(db: DbDependency, user: UserDependency, group_id: int):
    group = crud.get_group_by_id(db, group_id)
    if group is None or group.owner_id != user.id:
        return HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Grupo inexistente"
        )
    return group


################################################
# SPENDINGS
################################################


@app.post("/spending", status_code=HTTPStatus.CREATED)
def create_spending(
    spending: schemas.SpendingCreate, db: DbDependency, user: UserDependency
):
    return crud.create_spending(db, spending, user.id)


@app.get("/spending")
def list_spendings(db: DbDependency, user: UserDependency):
    return crud.get_spendings_by_owner_id(db, user.id)
