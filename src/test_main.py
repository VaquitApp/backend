import datetime
from http import HTTPStatus
from fastapi.testclient import TestClient
import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from .database import Base, SQLALCHEMY_DATABASE_URL
from .main import app, get_db


engine = create_engine(SQLALCHEMY_DATABASE_URL, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture()
def client():
    app.dependency_overrides[get_db] = override_get_db

    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def some_user_id(client: TestClient):
    response = client.post(
        url="/user/register",
        json={"email": "example@example.com", "password": "my_ultra_secret_password"},
    )
    assert response.status_code == HTTPStatus.CREATED
    return response.json()["id"]


################################################
# REGISTRATION
################################################


def test_register_a_user(client: TestClient):
    response = client.post(
        url="/user/register",
        json={"email": "example@example.com", "password": "my_ultra_secret_password"},
    )
    assert response.status_code == HTTPStatus.CREATED
    assert "id" in response.json()


def test_register_a_user_with_an_email_already_used(client: TestClient):
    first_response = client.post(
        url="/user/register",
        json={"email": "example@example.com", "password": "my_ultra_secret_password"},
    )

    assert first_response.status_code == HTTPStatus.CREATED
    assert "id" in first_response.json()

    second_response = client.post(
        url="/user/register",
        json={"email": "example@example.com", "password": "my_ultra_secret_password"},
    )

    assert second_response.status_code == 400


################################################
# LOGIN
################################################


def test_successful_login(client: TestClient):
    first_response = client.post(
        url="/user/register",
        json={"email": "example@example.com", "password": "my_ultra_secret_password"},
    )

    assert first_response.status_code == HTTPStatus.CREATED
    assert "id" in first_response.json()

    second_response = client.post(
        url="/user/login",
        json={"email": "example@example.com", "password": "my_ultra_secret_password"},
    )

    assert second_response.status_code == HTTPStatus.CREATED
    assert "token" in second_response.json()


def test_login_with_wrong_password(client: TestClient):
    first_response = client.post(
        url="/user/register",
        json={"email": "example@example.com", "password": "my_ultra_secret_password"},
    )

    assert first_response.status_code == HTTPStatus.CREATED
    assert "id" in first_response.json()

    second_response = client.post(
        url="/user/login",
        json={"email": "example@example.com", "password": "a_wrong_password"},
    )

    assert second_response.status_code == HTTPStatus.UNAUTHORIZED
    assert "token" not in second_response.json()


def test_login_with_wrong_email(client: TestClient):
    first_response = client.post(
        url="/user/register",
        json={"email": "example@example.com", "password": "my_ultra_secret_password"},
    )

    assert first_response.status_code == HTTPStatus.CREATED
    assert "id" in first_response.json()

    second_response = client.post(
        url="/user/login",
        json={
            "email": "example@a_wrong_domain.com",
            "password": "my_ultra_secret_password",
        },
    )

    assert second_response.status_code == HTTPStatus.NOT_FOUND
    assert "token" not in second_response.json()


################################################
# GROUPS
################################################


@pytest.fixture()
def some_group(client: TestClient, some_user_id: int):
    response = client.post(
        url="/group",
        json={"name": "grupo 1", "description": "really long description 1234"},
        headers={"x-user": str(some_user_id)},
    )

    assert response.status_code == HTTPStatus.CREATED
    response_body = response.json()
    assert "id" in response_body
    assert response_body["owner_id"] == some_user_id
    return response_body


def test_create_group(client: TestClient, some_group: int):
    # NOTE: test is inside fixture
    pass


def test_create_group_for_invalid_user(client: TestClient):
    first_response = client.post(
        url="/group",
        json={"name": "grupo 1", "description": "really long description 1234"},
        headers={"x-user": "5636262"},
    )

    assert first_response.status_code == HTTPStatus.UNAUTHORIZED


def test_get_newly_created_group(
    client: TestClient, some_user_id: int, some_group: int
):
    response = client.get(
        url="/group",
        headers={"x-user": str(some_user_id)},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == [some_group]


################################################
# SPENDINGS
################################################


def test_create_new_spending(client: TestClient, some_user_id: int):
    response = client.post(
        url="/spending",
        json={"amount": 500, "description": "bought some féca", "date": "2021-01-01"},
        headers={"x-user": str(some_user_id)},
    )

    assert response.status_code == HTTPStatus.CREATED
    response_body = response.json()
    assert "id" in response_body
    assert response_body["owner_id"] == some_user_id


def test_create_new_spending_with_default_date(client: TestClient, some_user_id: int):
    response = client.post(
        url="/spending",
        json={"amount": 500, "description": "bought some féca"},
        headers={"x-user": str(some_user_id)},
    )
    assert response.status_code == HTTPStatus.CREATED
    response_body = response.json()
    assert "id" in response_body
    assert response_body["owner_id"] == some_user_id
    assert datetime.datetime.fromisoformat(response_body["date"])


def test_get_spendings(client: TestClient, some_user_id: int):
    response = client.post(
        url="/spending",
        json={"amount": 500, "description": "bought some féca", "date": "2021-01-01"},
        headers={"x-user": str(some_user_id)},
    )

    assert response.status_code == HTTPStatus.CREATED
    spending = response.json()

    response = client.get(
        url="/spending",
        headers={"x-user": str(some_user_id)},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json() == [spending]
