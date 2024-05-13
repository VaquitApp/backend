import os
from sqlalchemy import create_engine, URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker


DB_NAME = os.environ.get("DB_NAME", "./sql_app.db")
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASSWORD")

# set automatically by kubernetes
# resolves to postgres service's host/port
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT")


SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_NAME}"

if DB_HOST is not None:
    SQLALCHEMY_DATABASE_URL = URL.create(
        "postgresql",
        username=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
    )

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass
