import os

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

ALGORITHM = "HS256"
RESOURCE_AUDIENCE = "resource-service"

bearer_scheme = HTTPBearer(auto_error=False)


def get_resource_jwt_secret():
    secret = os.environ.get("RESOURCE_JWT_SECRET")

    if not secret:
        raise RuntimeError("RESOURCE_JWT_SECRET environment variable is not set")

    return secret


def get_authority(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token required",
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            get_resource_jwt_secret(),
            algorithms=[ALGORITHM],
            audience=RESOURCE_AUDIENCE,
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authorization token",
        )

    if payload.get("sub") is None or payload.get("action") is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization token",
        )

    return payload


def require_action(authority: dict, expected_action: str):
    if authority.get("action") != expected_action:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Action not permitted",
        )


def require_role(authority: dict, expected_role: str):
    if authority.get("role") != expected_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Required role not present",
        )
