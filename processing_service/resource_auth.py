import os
from datetime import datetime, timedelta, timezone

import jwt

ALGORITHM = "HS256"
RESOURCE_AUDIENCE = "resource-service"
RESOURCE_TOKEN_EXPIRE_MINUTES = 5


def get_resource_jwt_secret():
    secret = os.environ.get("RESOURCE_JWT_SECRET")

    if not secret:
        raise RuntimeError("RESOURCE_JWT_SECRET environment variable is not set")

    return secret


def create_resource_token(
    action: str,
    document_id: int,
):
    now = datetime.now(timezone.utc)

    payload = {
        "sub": "processing-service",
        "aud": RESOURCE_AUDIENCE,
        "action": action,
        "resource_id": document_id,
        "iat": now,
        "exp": now + timedelta(minutes=RESOURCE_TOKEN_EXPIRE_MINUTES),
    }

    return jwt.encode(
        payload,
        get_resource_jwt_secret(),
        algorithm=ALGORITHM,
    )
