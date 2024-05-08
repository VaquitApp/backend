from fastapi import Depends, FastAPI, HTTPException
from . import crud, models, schemas
from .database import SessionLocal, engine
from sqlalchemy.orm import Session
import hashlib

models.Base.metadata.create_all(bind=engine)

app = FastAPI()


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/user/register")
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)

    if db_user is not None:
        raise HTTPException(status_code=400, detail="Email already registered")

    db_user = crud.create_user(db, user)

    return {"id": db_user.id}


@app.post("/user/login")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)

    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    hashed_password = hashlib.sha256(user.password.encode(encoding="utf-8")).hexdigest()

    if db_user.password != hashed_password:
        raise HTTPException(status_code=404, detail="Verify your credentials")

    return {"token": db_user.id}
