from fastapi.testclient import TestClient
import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


from .database import Base
from .main import app, get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture()
def set_up_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

################################################
# REGISTRATION
################################################

def test_register_a_user(set_up_db):
    response = client.post(
        url = "/user/register",
        json = {"email":"example@example.com", "password":"my_ultra_secret_password"},
    )
    assert response.status_code == 200
    assert 'id' in response.json()

def test_register_a_user_with_an_email_already_used(set_up_db):
    first_response = client.post(
        url = "/user/register",
        json = {"email":"example@example.com", "password":"my_ultra_secret_password"},
    )
    
    assert first_response.status_code == 200
    assert 'id' in first_response.json()
    
    second_response = client.post(
        url = "/user/register",
        json = {"email":"example@example.com", "password":"my_ultra_secret_password"},
    )

    assert second_response.status_code == 400

################################################
# LOGIN
################################################

def test_successful_login(set_up_db):
    first_response = client.post(
        url = "/user/register",
        json = {"email":"example@example.com", "password":"my_ultra_secret_password"},
    )
    
    assert first_response.status_code == 200
    assert 'id' in first_response.json()

    second_response = client.post(
        url = "/user/login",
        json = {"email":"example@example.com", "password":"my_ultra_secret_password"},
    )

    assert second_response.status_code == 200
    assert 'token' in second_response.json()


def test_login_with_wrong_password(set_up_db):
    first_response = client.post(
        url = "/user/register",
        json = {"email":"example@example.com", "password":"my_ultra_secret_password"},
    )
    
    assert first_response.status_code == 200
    assert 'id' in first_response.json()

    second_response = client.post(
        url = "/user/login",
        json = {"email":"example@example.com", "password":"a_wrong_password"},
    )

    assert second_response.status_code == 404
    assert 'token' not in second_response.json()

def test_login_with_wrong_email(set_up_db):
    first_response = client.post(
        url = "/user/register",
        json = {"email":"example@example.com", "password":"my_ultra_secret_password"},
    )
    
    assert first_response.status_code == 200
    assert 'id' in first_response.json()

    second_response = client.post(
        url = "/user/login",
        json = {"email":"example@a_wrong_domain.com", "password":"my_ultra_secret_password"},
    )

    assert second_response.status_code == 404
    assert 'token' not in second_response.json()
