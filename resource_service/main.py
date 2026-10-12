from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel

from resource_service.auth import get_authority, require_action
from resource_service.database import (
    create_document as db_create_document,
    get_document_by_id,
    initialize_database,
    list_documents_for_owner,
    search_documents_for_owner,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="Resource Service",
    lifespan=lifespan,
)


class DocumentCreate(BaseModel):
    title: str
    content: str


@app.get("/")
def root():
    return {
        "service": "resource-service",
        "message": "Resource Service is running",
    }


@app.get("/health")
def health():
    return {
        "service": "resource-service",
        "status": "ok",
    }


@app.post(
    "/documents",
    status_code=status.HTTP_201_CREATED,
)
def create_document(
    document: DocumentCreate,
    authority=Depends(get_authority),
):
    require_action(authority, "create_document")

    return db_create_document(
        owner_id=authority["sub"],
        title=document.title,
        content=document.content,
    )


@app.get("/documents")
def list_documents(authority=Depends(get_authority)):
    require_action(authority, "list_documents")

    return list_documents_for_owner(authority["sub"])


@app.get("/documents/search")
def search_documents(
    q: str,
    authority=Depends(get_authority),
):
    require_action(authority, "search_documents")

    return search_documents_for_owner(
        owner_id=authority["sub"],
        query=q,
    )


@app.get("/documents/{document_id}")
def get_document(
    document_id: int,
    authority=Depends(get_authority),
):
    require_action(authority, "read_document")

    if authority.get("resource_id") != document_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token is not valid for this resource",
        )

    document = get_document_by_id(document_id)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Document's owner is intentionally not checked in this vulnerable version
    return document
