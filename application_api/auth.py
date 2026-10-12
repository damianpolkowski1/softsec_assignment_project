import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from application_api.users import USERS

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 30
RESOURCE_TOKEN_EXPIRE_MINUTES = 5

APPLICATION_AUDIENCE = "application-api"
RESOURCE_AUDIENCE = "resource-service"

bearer_scheme = HTTPBearer(auto_error=False)


def get_jwt_secret():
    secret = os.environ.get("JWT_SECRET")

    if not secret:
        raise RuntimeError("JWT_SECRET environment variable is not set")

    return secret


def get_resource_jwt_secret():
    secret = os.environ.get("RESOURCE_JWT_SECRET")

    if not secret:
        raise RuntimeError("RESOURCE_JWT_SECRET environment variable is not set")

    return secret


def verify_password(plain_password: str, password_hash: str):
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        password_hash.encode("utf-8"),
    )


def create_access_token(username: str, role: str):
    now = datetime.now(timezone.utc)

    payload = {
        "sub": username,
        "role": role,
        "aud": APPLICATION_AUDIENCE,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }

    return jwt.encode(
        payload,
        get_jwt_secret(),
        algorithm=ALGORITHM,
    )


def create_resource_token(
    username: str,
    action: str,
    resource_id: int | None = None,
):
    now = datetime.now(timezone.utc)

    payload = {
        "sub": username,
        "aud": RESOURCE_AUDIENCE,
        "action": action,
        "iat": now,
        "exp": now + timedelta(minutes=RESOURCE_TOKEN_EXPIRE_MINUTES),
    }

    if resource_id is not None:
        payload["resource_id"] = resource_id

    return jwt.encode(
        payload,
        get_resource_jwt_secret(),
        algorithm=ALGORITHM,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            get_jwt_secret(),
            algorithms=[ALGORITHM],
            audience=APPLICATION_AUDIENCE,
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    username = payload.get("sub")

    if username is None or username not in USERS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )

    return USERS[username]
