from fastapi.testclient import TestClient
from .main import app
import os
import time

client = TestClient(app)

################################################
# REGISTRATION
################################################

def test_register_a_user():
    response = client.post(
        url = "/user/register",
        json = {"email":"example@example.com", "password":"my_ultra_secret_password"},
    )
    assert response.status_code == 200
    assert 'id' in response.json()

def test_register_a_user_with_an_email_already_used():
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

def test_successful_login():
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


def test_login_with_wrong_password():
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

def test_login_with_wrong_email():
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
