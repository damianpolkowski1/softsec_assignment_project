from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel

from application_api.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_current_user,
    verify_password,
)
from application_api.users import USERS

app = FastAPI(title="Application API")


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


@app.get("/")
def root():
    return {
        "service": "application-api",
        "message": "Application API is running",
    }


@app.get("/health")
def health():
    return {
        "service": "application-api",
        "status": "ok",
    }


@app.post("/login", response_model=TokenResponse)
def login(login_request: LoginRequest):
    user = USERS.get(login_request.username)

    if user is None or not verify_password(
        login_request.password,
        user["password_hash"],
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    access_token = create_access_token(
        username=user["username"],
        role=user["role"],
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@app.get("/me")
def get_me(current_user=Depends(get_current_user)):
    return {
        "username": current_user["username"],
        "role": current_user["role"],
    }
