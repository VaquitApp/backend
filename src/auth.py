import hashlib
from typing import Optional
from jose import JWTError, jwt
import time

from src.models import User
from src.schemas import UserCredentials

# TODO: fetch this secret from environment variable
JWT_SECRET = "myjwtsecret"
DEFAULT_EXPIRY = 30 * 24 * 60 * 60  # 30 days


def compute_password_hash(password: str) -> str:
    return hashlib.sha256(password.encode(encoding="utf-8")).hexdigest()


def valid_password(password: str, hashed_password: bytes) -> str:
    return hashed_password == compute_password_hash(password)


def login_user(user: User) -> UserCredentials:
    user_info = {"id": user.id, "email": user.email}
    claims = generate_jwt_claims(user.id)
    token = jwt.encode({**claims, **user_info}, JWT_SECRET, algorithm="HS256")
    return UserCredentials(**user_info, jwt=token)


def generate_jwt_claims(user_id: int) -> dict:
    now = int(time.time())
    return {"sub": str(user_id), "iat": now, "nbf": now, "exp": now + DEFAULT_EXPIRY}


def parse_jwt(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except JWTError:
        return None
