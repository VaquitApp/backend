import datetime
from http import HTTPStatus
from uuid import uuid4
from fastapi.testclient import TestClient
import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.mail import LocalMailSender
from src.main import app, get_db, get_mail_sender
from src.database import Base, SQLALCHEMY_DATABASE_URL
from src import schemas, auth


engine = create_engine(SQLALCHEMY_DATABASE_URL, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


def override_get_mail_sender():
    return LocalMailSender()


@pytest.fixture()
def client():
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_mail_sender] = override_get_mail_sender

    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def some_credentials(client: TestClient) -> schemas.UserCredentials:
    response = client.post(
        url="/user/register",
        json={"email": "example@example.com", "password": "my_ultra_secret_password"},
    )
    assert response.status_code == HTTPStatus.CREATED
    return schemas.UserCredentials(**response.json())


@pytest.fixture()
def some_other_credentials(client: TestClient) -> schemas.UserCredentials:
    response = client.post(
        url="/user/register",
        json={"email": "example2@example.com", "password": "my_ultra_secret_password"},
    )
    assert response.status_code == HTTPStatus.CREATED
    return schemas.UserCredentials(**response.json())


################################################
# REGISTRATION
################################################


def test_register_a_user(client: TestClient):
    email = "example@example.com"
    response = client.post(
        url="/user/register",
        json={"email": email, "password": "my_ultra_secret_password"},
    )
    assert response.status_code == HTTPStatus.CREATED
    body = response.json()
    assert "id" in body
    assert "jwt" in body
    assert body["email"] == email
    assert auth.parse_jwt(body["jwt"]) is not None


def test_register_a_user_with_an_email_already_used(
    client: TestClient, some_credentials: schemas.UserCredentials
):
    second_response = client.post(
        url="/user/register",
        json={"email": some_credentials.email, "password": "some_other_password"},
    )

    assert second_response.status_code == HTTPStatus.BAD_REQUEST


################################################
# LOGIN
################################################


def test_successful_login(client: TestClient):
    post_body = {"email": "example@example.com", "password": "my_ultra_secret_password"}

    # Register the user
    first_response = client.post(url="/user/register", json=post_body)

    assert first_response.status_code == HTTPStatus.CREATED

    # Login the user
    second_response = client.post(url="/user/login", json=post_body)

    assert second_response.status_code == HTTPStatus.CREATED
    body = second_response.json()
    assert "id" in body
    assert "jwt" in body
    assert body["email"] == post_body["email"]
    assert auth.parse_jwt(body["jwt"]) is not None


def test_login_with_wrong_password(client: TestClient):
    first_response = client.post(
        url="/user/register",
        json={"email": "example@example.com", "password": "my_ultra_secret_password"},
    )

    assert first_response.status_code == HTTPStatus.CREATED
    assert "jwt" in first_response.json()

    second_response = client.post(
        url="/user/login",
        json={"email": "example@example.com", "password": "a_wrong_password"},
    )

    assert second_response.status_code == HTTPStatus.UNAUTHORIZED
    assert "jwt" not in second_response.json()


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
def some_group(client: TestClient, some_credentials: schemas.UserCredentials):
    response = client.post(
        url="/group",
        json={"name": "grupo 1", "description": "really long description 1234"},
        headers={"x-user": some_credentials.jwt},
    )

    assert response.status_code == HTTPStatus.CREATED
    response_body = response.json()
    assert "id" in response_body
    assert response_body["owner_id"] == some_credentials.id
    return schemas.Group(**response_body)


def test_create_group(client: TestClient, some_group: schemas.Group):
    # NOTE: test is inside fixture
    pass


def test_get_created_group(
    client: TestClient,
    some_group: schemas.Group,
    some_credentials: schemas.UserCredentials,
):
    response = client.get(
        url=f"/group/{some_group.id}",
        headers={"x-user": some_credentials.jwt},
    )

    assert response.status_code == HTTPStatus.OK
    assert schemas.Group(**response.json()) == some_group


def test_get_group_members_with_only_owner(
    client: TestClient,
    some_group: schemas.Group,
    some_credentials: schemas.UserCredentials,
):
    response = client.get(
        url=f"/group/{some_group.id}/member",
        headers={"x-user": some_credentials.jwt},
    )

    body = response.json()

    assert response.status_code == HTTPStatus.OK
    assert len(body) == 1
    assert body[0]["id"] == some_credentials.id
    assert body[0]["email"] == some_credentials.email


def test_create_group_for_invalid_user(client: TestClient):
    first_response = client.post(
        url="/group",
        json={"name": "grupo 1", "description": "really long description 1234"},
        headers={"x-user": "5636262"},
    )

    assert first_response.status_code == HTTPStatus.UNAUTHORIZED


def test_get_newly_created_group(
    client: TestClient,
    some_credentials: schemas.UserCredentials,
    some_group: schemas.Group,
):
    response = client.get(
        url="/group",
        headers={"x-user": some_credentials.jwt},
    )

    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 1
    assert schemas.Group(**response.json()[0]) == some_group


def test_correctly_archive_group(
    client: TestClient,
    some_credentials: schemas.UserCredentials,
    some_group: schemas.Group,
):
    response = client.put(
        url=f"/group/{some_group.id}/archive", headers={"x-user": some_credentials.jwt}
    )

    assert response.status_code == HTTPStatus.OK

    response = client.get(
        url=f"/group/{some_group.id}",
        headers={"x-user": some_credentials.jwt},
    )
    assert response.status_code == HTTPStatus.OK
    assert schemas.Group(**response.json()).is_archived


def test_alter_state_of_non_existant_group(
    client: TestClient,
    some_credentials: schemas.UserCredentials,
    some_group: schemas.Group,
):
    response = client.put(
        url=f"/group/{some_group.id+1}/archive",
        headers={"x-user": some_credentials.jwt},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_update_group_correctly(
    client: TestClient,
    some_credentials: schemas.UserCredentials,
    some_group: schemas.Group,
):
    put_body = {
        "id": some_group.id,
        "name": "TESTING",
        "description": "TESTING",
    }
    response = client.put(
        url="/group", headers={"x-user": some_credentials.jwt}, json=put_body
    )
    assert response.status_code == HTTPStatus.OK
    response_group = schemas.Group(**response.json())
    assert response_group.name != some_group.name
    assert response_group.description != some_group.description


def test_update_group_non_existant(
    client: TestClient,
    some_credentials: schemas.UserCredentials,
):
    put_body = {
        "id": 27,
        "name": "TESTING",
        "description": "TESTING",
    }
    response = client.put(
        url=f"/group", headers={"x-user": some_credentials.jwt}, json=put_body
    )
    assert response.status_code == HTTPStatus.NOT_FOUND


################################################
# CATEGORIES
################################################


@pytest.fixture
def some_category(
    client: TestClient,
    some_credentials: schemas.UserCredentials,
    some_group: schemas.Group,
):
    response = client.post(
        url="/category",
        json={"name": "cafe", "group_id": some_group.id},
        headers={"x-user": some_credentials.jwt},
    )

    assert response.status_code == HTTPStatus.CREATED
    response_body = response.json()
    assert response_body["name"] == "cafe"
    assert response_body["group_id"] == some_group.id
    return response_body


def test_create_new_category(client: TestClient, some_category: schemas.Category):
    # NOTE: test is inside fixture
    pass


def test_add_user_to_group(
    client: TestClient,
    some_credentials: schemas.UserCredentials,
    some_group: schemas.Group,
):
    # Create new user
    body = {"email": "some_email@example.com", "password": "some_password"}
    response = client.post(url="/user/register", json=body)
    assert response.status_code == HTTPStatus.CREATED
    user = response.json()

    # Add new user to group
    response = client.post(
        url=f"/group/{some_group.id}/member",
        headers={"x-user": some_credentials.jwt},
        json={"user_id": user["id"]},
    )
    body = response.json()
    assert response.status_code == HTTPStatus.CREATED
    assert len(body) == 2
    assert sorted([u["id"] for u in body]) == sorted([some_credentials.id, user["id"]])

    # GET group members
    response = client.get(
        url=f"/group/{some_group.id}/member",
        headers={"x-user": some_credentials.jwt},
    )

    body = response.json()

    assert response.status_code == HTTPStatus.OK
    assert len(body) == 2
    assert sorted([u["id"] for u in body]) == sorted([some_credentials.id, user["id"]])


################################################
# SPENDINGS
################################################


@pytest.fixture
def some_spending(
    client: TestClient,
    some_credentials: schemas.UserCredentials,
    some_group: schemas.Group,
    some_category: schemas.Category,
):
    response = client.post(
        url="/spending",
        json={
            "amount": 500,
            "description": "bought some féca",
            "date": "2021-01-01",
            "group_id": some_group.id,
            "category_id": some_category.id,
        },
        headers={"x-user": some_credentials.jwt},
    )

    assert response.status_code == HTTPStatus.CREATED
    response_body = response.json()
    assert "id" in response_body
    assert response_body["group_id"] == some_group.id
    assert response_body["category_id"] == some_category.id
    assert response_body
    return schemas.Spending(**response_body)


def test_create_new_spending(client: TestClient, some_spending: schemas.Spending):
    # NOTE: test is inside fixture
    pass


def test_create_new_spending_with_default_date(
    client: TestClient,
    some_credentials: schemas.UserCredentials,
    some_group: schemas.Group,
    some_category: schemas.Category,
):
    response = client.post(
        url="/spending",
        json={
            "amount": 500,
            "description": "bought some féca",
            "group_id": some_group.id,
            "category_id": some_category.id,
        },
        headers={"x-user": some_credentials.jwt},
    )
    assert response.status_code == HTTPStatus.CREATED
    response_body = response.json()
    assert "id" in response_body
    assert response_body["group_id"] == some_group.id
    assert response_body["category_id"] == some_category.id
    assert datetime.datetime.fromisoformat(response_body["date"])


def test_create_new_spending_with_non_existant_category(
    client: TestClient,
    some_credentials: schemas.UserCredentials,
    some_group: schemas.Group,
):
    response = client.post(
        url="/spending",
        json={
            "amount": 500,
            "description": "bought some féca",
            "group_id": some_group.id,
            "category_id": 61623,
        },
        headers={"x-user": some_credentials.jwt},
    )
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_get_spendings(
    client: TestClient,
    some_credentials: schemas.UserCredentials,
    some_spending: schemas.Spending,
):
    response = client.get(
        url="/spending",
        params={"group_id": some_spending.group_id},
        headers={"x-user": some_credentials.jwt},
    )
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 1
    assert schemas.Spending(**response.json()[0]) == some_spending


def test_create_spending_on_archived_group(
    client: TestClient,
    some_credentials: schemas.UserCredentials,
    some_group: schemas.Group,
    some_category: schemas.Category,
):

    response = client.put(
        url=f"/group/{some_group.id}/archive", headers={"x-user": some_credentials.jwt}
    )
    assert response.status_code == HTTPStatus.OK

    response = client.post(
        url="/spending",
        json={
            "amount": 500,
            "description": "bought some féca",
            "group_id": some_group.id,
            "category_id": some_category.id,
        },
        headers={"x-user": some_credentials.jwt},
    )
    assert response.status_code == HTTPStatus.NOT_ACCEPTABLE


################################################
# BUDGETS
################################################


@pytest.fixture
def some_budget(
    client: TestClient,
    some_credentials: schemas.UserCredentials,
    some_category: schemas.Category,
    some_group: schemas.Group,
):
    response = client.post(
        url="/budget",
        json={
            "amount": 500,
            "description": "café",
            "start_date": "2021-01-01",
            "end_date": "2021-02-01",
            "group_id": some_group.id,
            "category_id": some_category.id,
        },
        headers={"x-user": some_credentials.jwt},
    )

    assert response.status_code == HTTPStatus.CREATED
    response_body = response.json()
    assert "id" in response_body
    assert response_body["group_id"] == some_group.id
    return schemas.Budget(**response_body)


def test_create_new_budget(client: TestClient, some_budget: schemas.Budget):
    # NOTE: test is inside fixture
    pass


def test_get_budget(
    client: TestClient,
    some_credentials: schemas.UserCredentials,
    some_budget: schemas.Budget,
):
    response = client.get(
        url=f"/budget/{some_budget.id}",
        headers={"x-user": some_credentials.jwt},
    )

    assert response.status_code == HTTPStatus.OK
    assert schemas.Budget(**response.json()) == some_budget


def test_put_budget(
    client: TestClient,
    some_credentials: schemas.UserCredentials,
    some_budget: schemas.Budget,
):
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
        headers={"x-user": some_credentials.jwt},
    )

    assert response.status_code == HTTPStatus.OK

    response = client.get(
        url=f"/budget/{some_budget.id}",
        headers={"x-user": some_credentials.jwt},
    )
    assert response.status_code == HTTPStatus.OK
    for k, v in put_body.items():
        assert response.json()[k] == v


def test_get_group_budgets(
    client: TestClient,
    some_credentials: schemas.UserCredentials,
    some_budget: schemas.Budget,
):
    response = client.get(
        url=f"/group/{some_budget.group_id}/budget",
        headers={"x-user": some_credentials.jwt},
    )

    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 1
    assert schemas.Budget(**response.json()[0]) == some_budget


def test_create_budget_on_archived_group(
    client: TestClient,
    some_credentials: schemas.UserCredentials,
    some_group: schemas.Group,
):

    response = client.put(
        url=f"/group/{some_group.id}/archive", headers={"x-user": some_credentials.jwt}
    )
    assert response.status_code == HTTPStatus.OK

    response = client.post(
        url="/budget",
        json={
            "amount": 1000,
            "description": "MAS CAFE AAAA",
            "start_date": "2021-01-01",
            "end_date": "2021-02-01",
            "group_id": some_group.id,
            "category_id": 1,
        },
        headers={"x-user": some_credentials.jwt},
    )
    assert response.status_code == HTTPStatus.NOT_ACCEPTABLE


################################################
# CATEGORIES
################################################
# TODO
@pytest.fixture()
def some_category(
    client: TestClient,
    some_credentials: schemas.UserCredentials,
    some_group: schemas.Group,
):
    response = client.post(
        url="/category",
        json={
            "name": "nombre_categoria",
            "description": "really long description 1234",
            "group_id": 1,
            "strategy": "a cool strategy",
        },
        headers={"x-user": some_credentials.jwt},
    )

    assert response.status_code == HTTPStatus.CREATED
    response_body = response.json()
    assert response_body["group_id"] == some_group.id
    return schemas.Category(**response_body)


def test_category_delete(
    client: TestClient,
    some_credentials: schemas.UserCredentials,
    some_category: schemas.Category,
):
    response = client.request(
        method="DELETE",
        url=f"/category/{some_category.id}",
        headers={"x-user": some_credentials.jwt},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == some_category.model_dump()


def test_category_modify_name(
    client: TestClient,
    some_credentials: schemas.UserCredentials,
    some_category: schemas.Category,
):
    response = client.put(
        url=f"/category/{some_category.id}",
        json={
            "name": "nuevo nombre categoria",
            "description": "otra descripcion",
            # TODO: move strategy to enums
            "strategy": "equitativo?",
        },
        headers={"x-user": some_credentials.jwt},
    )

    assert response.status_code == HTTPStatus.OK
    response_body = response.json()
    assert "group_id" in response_body
    assert response_body["name"] == "nuevo nombre categoria"
    assert response_body["description"] == "otra descripcion"


################################################
# INVITES
################################################


@pytest.fixture
def some_invite(
    client: TestClient,
    some_credentials: schemas.UserCredentials,
    some_other_credentials: schemas.UserCredentials,
    some_group: schemas.Group,
):

    # Create Invite
    response = client.post(
        url="/invite",
        json={
            "receiver_email": some_other_credentials.email,
            "group_id": some_group.id,
        },
        headers={"x-user": some_credentials.jwt},
    )
    assert response.status_code == HTTPStatus.CREATED
    response_body = response.json()

    assert "creation_date" in response_body
    assert "token" in response_body
    assert response_body["status"] == schemas.InviteStatus.PENDING
    assert response_body["group_id"] == some_group.id
    assert response_body["sender_id"] == some_credentials.id
    assert response_body["receiver_id"] == some_other_credentials.id

    return schemas.Invite(**response_body)


def test_create_invite(client: TestClient, some_invite: schemas.Invite):
    # NOTE: test is inside fixture
    pass


def test_get_invite_by_id(
    client: TestClient,
    some_invite: schemas.Invite,
):
    response = client.get(
        url=f"/invite/{some_invite.token}",
    )
    assert response.status_code == HTTPStatus.OK
    assert schemas.Invite(**response.json()) == some_invite


def test_get_invite_by_non_existant_id(client: TestClient):
    response = client.get(
        url=f"/invite/{uuid4().hex}",
    )
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_send_group_invite_to_non_registered_user(
    client: TestClient,
    some_credentials: schemas.UserCredentials,
    some_group: schemas.Group,
):

    response = client.post(
        url="/invite",
        json={"receiver_email": "pepe@gmail.com", "group_id": some_group.id},
        headers={"x-user": some_credentials.jwt},
    )
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_send_group_invite_non_existant_group(
    client: TestClient, some_credentials: schemas.UserCredentials
):
    response = client.post(
        url="/invite",
        json={"receiver_email": some_credentials.email, "group_id": 12345},
        headers={"x-user": some_credentials.jwt},
    )
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_send_group_invite_to_already_member(
    client: TestClient,
    some_group: schemas.Group,
    some_credentials: schemas.UserCredentials,
):
    response = client.post(
        url="/invite",
        json={"receiver_email": some_credentials.email, "group_id": some_group.id},
        headers={"x-user": some_credentials.jwt},
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_send_group_invite_from_non_group_member(
    client: TestClient,
    some_credentials: schemas.UserCredentials,
    some_other_credentials: schemas.UserCredentials,
):

    # Other Group
    response = client.post(
        url="/group",
        json={"name": "grupo 2", "description": "really long description 1234"},
        headers={"x-user": some_other_credentials.jwt},
    )
    assert response.status_code == HTTPStatus.CREATED
    new_group_id = response.json()["id"]

    # Send Invite With Wrong Owner
    response = client.post(
        url="/invite",
        json={"receiver_email": some_credentials.email, "group_id": new_group_id},
        headers={"x-user": some_credentials.jwt},
    )
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_join_group(
    client: TestClient,
    some_credentials: schemas.UserCredentials,
    some_other_credentials: schemas.UserCredentials,
    some_group: schemas.Group,
    some_invite: schemas.Invite,
):
    response = client.post(
        url=f"/invite/join/{some_invite.token.hex}",
        headers={"x-user": some_other_credentials.jwt},
    )
    assert response.status_code == HTTPStatus.OK
    assert schemas.Invite(**response.json()).status == schemas.InviteStatus.ACCEPTED

    response = client.get(
        url=f"/group/{some_group.id}/member",
        headers={"x-user": some_credentials.jwt},
    )
    assert len(response.json()) == 2


def test_try_join_invalid_token(
    client: TestClient,
    some_credentials: schemas.UserCredentials,
):
    response = client.post(
        url=f"/invite/join/{uuid4().hex}",
        headers={"x-user": some_credentials.jwt},
    )
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_try_join_group_as_wrong_user(
    client: TestClient,
    some_credentials: schemas.UserCredentials,
    some_invite: schemas.Invite,
):

    response = client.post(
        url=f"/invite/join/{some_invite.token.hex}",
        headers={"x-user": some_credentials.jwt},
    )
    assert response.status_code == HTTPStatus.FORBIDDEN


def test_try_join_archived_group(
    client: TestClient,
    some_credentials: schemas.UserCredentials,
    some_other_credentials: schemas.UserCredentials,
    some_group: schemas.Group,
    some_invite: schemas.Invite,
):

    response = client.put(
        url=f"/group/{some_group.id}/archive", headers={"x-user": some_credentials.jwt}
    )
    assert response.status_code == HTTPStatus.OK

    response = client.post(
        url=f"/invite/join/{some_invite.token.hex}",
        headers={"x-user": some_other_credentials.jwt},
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_try_join_already_member(
    client: TestClient,
    some_other_credentials: schemas.UserCredentials,
    some_invite: schemas.Invite,
):

    response = client.post(
        url=f"/invite/join/{some_invite.token.hex}",
        headers={"x-user": some_other_credentials.jwt},
    )
    assert response.status_code == HTTPStatus.OK

    response = client.post(
        url=f"/invite/join/{some_invite.token.hex}",
        headers={"x-user": some_other_credentials.jwt},
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
