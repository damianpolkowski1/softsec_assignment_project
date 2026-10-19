from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Any

from resource_service.auth import (
    get_authority,
    require_action,
    require_role,
)
from resource_service.database import (
    create_document as db_create_document,
    store_analysis_result as db_store_analysis_result,
    get_document_by_id,
    initialize_database,
    list_documents_for_owner,
    search_documents_for_owner,
    get_analysis_result_by_id,
    list_all_document_metadata,
    read_result_file,
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


class AnalysisStoreRequest(BaseModel):
    document_id: int
    analysis: dict[str, Any]


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

    if document["owner_id"] != authority["sub"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this document",
        )

    return document


@app.get("/internal/documents/{document_id}")
def get_document_for_processing(
    document_id: int,
    authority=Depends(get_authority),
):
    require_action(
        authority,
        "processing_read_document",
    )

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

    return document


@app.post(
    "/internal/analysis-results",
    status_code=status.HTTP_201_CREATED,
)
def store_analysis_result(
    request: AnalysisStoreRequest,
    authority=Depends(get_authority),
):
    require_action(
        authority,
        "store_analysis_result",
    )

    if authority.get("resource_id") != request.document_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token is not valid for this resource",
        )

    result = db_store_analysis_result(
        document_id=request.document_id,
        analysis=request.analysis,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return result


@app.get("/analysis-results/{result_id}")
def get_analysis_result(
    result_id: int,
    authority=Depends(get_authority),
):
    require_action(
        authority,
        "read_analysis_result",
    )

    if authority.get("resource_id") != result_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token is not valid for this resource",
        )

    result = get_analysis_result_by_id(result_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis result not found",
        )

    if result["owner_id"] != authority["sub"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this analysis result",
        )

    content = read_result_file(result["result_filename"])

    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result file not found",
        )

    return {
        "result_id": result["id"],
        "document_id": result["document_id"],
        "content": content,
    }


@app.get("/admin/documents/metadata")
def get_all_document_metadata(
    authority=Depends(get_authority),
):
    require_action(
        authority,
        "list_all_document_metadata",
    )

    require_role(
        authority,
        "ADMIN",
    )

    return list_all_document_metadata()
