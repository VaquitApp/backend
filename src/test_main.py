import datetime
from http import HTTPStatus
from fastapi.testclient import TestClient
import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


from .main import app, get_db
from .database import Base, SQLALCHEMY_DATABASE_URL
from . import schemas


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
    return schemas.Group(**response_body)


def test_create_group(client: TestClient, some_group: schemas.Group):
    # NOTE: test is inside fixture
    pass


def test_get_created_group(
    client: TestClient, some_group: schemas.Group, some_user_id: int
):
    response = client.get(
        url=f"/group/{some_group.id}",
        headers={"x-user": str(some_user_id)},
    )

    assert response.status_code == HTTPStatus.OK
    assert schemas.Group(**response.json()) == some_group


def test_create_group_for_invalid_user(client: TestClient):
    first_response = client.post(
        url="/group",
        json={"name": "grupo 1", "description": "really long description 1234"},
        headers={"x-user": "5636262"},
    )

    assert first_response.status_code == HTTPStatus.UNAUTHORIZED


def test_get_newly_created_group(
    client: TestClient, some_user_id: int, some_group: schemas.Group
):
    response = client.get(
        url="/group",
        headers={"x-user": str(some_user_id)},
    )

    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 1
    assert schemas.Group(**response.json()[0]) == some_group


################################################
# SPENDINGS
################################################


@pytest.fixture
def some_spending(client: TestClient, some_user_id: int, some_group: schemas.Group):
    response = client.post(
        url="/spending",
        json={
            "amount": 500,
            "description": "bought some féca",
            "date": "2021-01-01",
            "group_id": some_group.id,
        },
        headers={"x-user": str(some_user_id)},
    )

    assert response.status_code == HTTPStatus.CREATED
    response_body = response.json()
    assert "id" in response_body
    assert response_body["group_id"] == some_group.id
    return schemas.Spending(**response_body)


def test_create_new_spending(client: TestClient, some_spending: schemas.Spending):
    # NOTE: test is inside fixture
    pass


def test_create_new_spending_with_default_date(
    client: TestClient, some_user_id: int, some_group: schemas.Group
):
    response = client.post(
        url="/spending",
        json={
            "amount": 500,
            "description": "bought some féca",
            "group_id": some_group.id,
        },
        headers={"x-user": str(some_user_id)},
    )
    assert response.status_code == HTTPStatus.CREATED
    response_body = response.json()
    assert "id" in response_body
    assert response_body["group_id"] == some_group.id
    assert datetime.datetime.fromisoformat(response_body["date"])


def test_get_spendings(
    client: TestClient, some_user_id: int, some_spending: schemas.Spending
):
    response = client.get(
        url="/spending",
        params={"group_id": some_spending.group_id},
        headers={"x-user": str(some_user_id)},
    )
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 1
    assert schemas.Spending(**response.json()[0]) == some_spending


################################################
# BUDGETS
################################################


@pytest.fixture
def some_budget(client: TestClient, some_user_id: int, some_group: schemas.Group):
    response = client.post(
        url="/budget",
        json={
            "amount": 500,
            "description": "café",
            "start_date": "2021-01-01",
            "end_date": "2021-02-01",
            "group_id": some_group.id,
            "category_id": 1,
        },
        headers={"x-user": str(some_user_id)},
    )

    assert response.status_code == HTTPStatus.CREATED
    response_body = response.json()
    assert "id" in response_body
    assert response_body["group_id"] == some_group.id
    return schemas.Budget(**response_body)


def test_create_new_budget(client: TestClient, some_budget: schemas.Budget):
    # NOTE: test is inside fixture
    pass


def test_get_budget(client: TestClient, some_user_id: int, some_budget: schemas.Budget):
    response = client.get(
        url=f"/budget/{some_budget.id}",
        headers={"x-user": str(some_user_id)},
    )

    assert response.status_code == HTTPStatus.OK
    assert schemas.Budget(**response.json()) == some_budget


def test_put_budget(client: TestClient, some_user_id: int, some_budget: schemas.Budget):
    put_body = {
        "amount": 1000,
        "description": "some other description",
        "start_date": "2021-03-01T00:00:00",
        "end_date": "2021-04-01T00:00:00",
        "category_id": 2,
    }
    response = client.put(
        url=f"/budget/{some_budget.id}",
        json=put_body,
        headers={"x-user": str(some_user_id)},
    )

    assert response.status_code == HTTPStatus.OK

    response = client.get(
        url=f"/budget/{some_budget.id}",
        headers={"x-user": str(some_user_id)},
    )
    assert response.status_code == HTTPStatus.OK
    for k, v in put_body.items():
        assert response.json()[k] == v


def test_get_group_budgets(
    client: TestClient, some_user_id: int, some_budget: schemas.Budget
):
    response = client.get(
        url=f"/group/{some_budget.group_id}/budget",
        headers={"x-user": str(some_user_id)},
    )

    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 1
    assert schemas.Budget(**response.json()[0]) == some_budget
