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


def get_user(x_user: Annotated[int | None, Header()]) -> int:
    return x_user


app = FastAPI(dependencies=[Depends(get_db)])

DbDependency = Annotated[Session, Depends(get_db)]
UserDependency = Annotated[int, Depends(get_user)]


@app.post("/user/register", status_code=HTTPStatus.CREATED)
def create_user(user: schemas.UserCreate, db: DbDependency):
    db_user = crud.get_user_by_email(db, email=user.email)

    if db_user is not None:
        raise HTTPException(status_code=400, detail="Email ya existente")

    db_user = crud.create_user(db, user)

    return {"id": db_user.id}


@app.post("/user/login", status_code=HTTPStatus.CREATED)
def login(user: schemas.UserLogin, db: DbDependency):
    db_user = crud.get_user_by_email(db, email=user.email)

    if db_user is None:
        raise HTTPException(status_code=404, detail="Usuario no existe")

    hashed_password = hashlib.sha256(user.password.encode(encoding="utf-8")).hexdigest()

    if db_user.password != hashed_password:
        raise HTTPException(status_code=404, detail="Contraseña incorrecta")

    return {"token": db_user.id}


@app.post("/group", status_code=HTTPStatus.CREATED)
def create_group(group: schemas.GroupCreate, db: DbDependency, user_id: UserDependency):
    return crud.create_group(db, group, user_id)
