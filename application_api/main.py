import os

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel

from application_api.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    create_resource_token,
    get_current_user,
    verify_password,
)
from application_api.users import USERS

RESOURCE_SERVICE_URL = os.environ.get(
    "RESOURCE_SERVICE_URL",
    "http://127.0.0.1:8001",
)


app = FastAPI(title="Application API")


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class DocumentCreate(BaseModel):
    title: str
    content: str


def request_resource_service(
    method: str,
    path: str,
    authority_token: str,
    json_body: dict | None = None,
    params: dict | None = None,
):
    try:
        response = httpx.request(
            method=method,
            url=f"{RESOURCE_SERVICE_URL}{path}",
            headers={
                "Authorization": f"Bearer {authority_token}",
            },
            json=json_body,
            params=params,
            timeout=5.0,
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Resource Service unavailable",
        ) from exc

    if response.is_error:
        detail = "Resource Service request failed"

        try:
            detail = response.json().get("detail", detail)
        except ValueError:
            pass

        raise HTTPException(
            status_code=response.status_code,
            detail=detail,
        )

    return response.json()


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


@app.post(
    "/documents",
    status_code=status.HTTP_201_CREATED,
)
def create_document(
    document: DocumentCreate,
    current_user=Depends(get_current_user),
):
    authority_token = create_resource_token(
        username=current_user["username"],
        action="create_document",
    )

    return request_resource_service(
        method="POST",
        path="/documents",
        authority_token=authority_token,
        json_body=document.model_dump(),
    )


@app.get("/documents")
def list_documents(current_user=Depends(get_current_user)):
    authority_token = create_resource_token(
        username=current_user["username"],
        action="list_documents",
    )

    return request_resource_service(
        method="GET",
        path="/documents",
        authority_token=authority_token,
    )


@app.get("/documents/search")
def search_documents(
    q: str,
    current_user=Depends(get_current_user),
):
    authority_token = create_resource_token(
        username=current_user["username"],
        action="search_documents",
    )

    return request_resource_service(
        method="GET",
        path="/documents/search",
        authority_token=authority_token,
        params={"q": q},
    )


@app.get("/documents/{document_id}")
def get_document(
    document_id: int,
    current_user=Depends(get_current_user),
):
    authority_token = create_resource_token(
        username=current_user["username"],
        action="read_document",
        resource_id=document_id,
    )

    return request_resource_service(
        method="GET",
        path=f"/documents/{document_id}",
        authority_token=authority_token,
    )
