from http import HTTPStatus
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, Header

from src import crud, models, schemas, auth
from src.database import SessionLocal, engine
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
        raise HTTPException(
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
    # TODO: check group exists
    return crud.create_spending(db, spending, user.id)


@app.get("/spending")
def list_spendings(db: DbDependency, user: UserDependency, group_id: int):
    group = crud.get_group_by_id(db, group_id)
    # TODO: allow members to see spendings
    if group is None or group.owner_id != user.id:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Grupo inexistente"
        )
    return crud.get_spendings_by_group_id(db, group_id)


@app.get("/group/{group_id}/spending")
def list_group_spendings(db: DbDependency, user: UserDependency, group_id: int):
    group = crud.get_group_by_id(db, group_id)
    if group is None or group.owner_id != user.id:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Grupo inexistente"
        )
    return crud.get_spendings_by_group_id(db, group_id)


################################################
# BUDGETS
################################################


@app.post("/budget", status_code=HTTPStatus.CREATED)
def create_budget(
    spending: schemas.BudgetCreate, db: DbDependency, user: UserDependency
):
    # TODO: check group exists
    return crud.create_budget(db, spending)


@app.get("/budget/{budget_id}")
def get_budget(db: DbDependency, user: UserDependency, budget_id: int):
    return crud.get_budget_by_id(db, budget_id)


@app.put("/budget/{budget_id}")
def put_budget(
    db: DbDependency, user: UserDependency, budget_id: int, budget: schemas.BudgetPut
):
    return crud.put_budget(db, budget_id, budget)


@app.get("/group/{group_id}/budget")
def list_group_budgets(db: DbDependency, user: UserDependency, group_id: int):
    group = crud.get_group_by_id(db, group_id)
    if group is None or group.owner_id != user.id:
        return HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Grupo inexistente"
        )
    return crud.get_budgets_by_group_id(db, group_id)
