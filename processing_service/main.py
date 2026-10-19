import os

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel

from processing_service.auth import (
    get_processing_authority,
    require_action,
)
from processing_service.resource_auth import create_resource_token
from textstats_lib import analyze_text

RESOURCE_SERVICE_URL = os.environ.get(
    "RESOURCE_SERVICE_URL",
    "http://127.0.0.1:8001",
)


app = FastAPI(title="Processing Service")


class AnalysisRequest(BaseModel):
    document_id: int


def request_resource_service(
    method: str,
    path: str,
    authority_token: str,
    json_body: dict | None = None,
):
    try:
        response = httpx.request(
            method=method,
            url=f"{RESOURCE_SERVICE_URL}{path}",
            headers={
                "Authorization": f"Bearer {authority_token}",
            },
            json=json_body,
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
        "service": "processing-service",
        "message": "Processing Service is running",
    }


@app.get("/health")
def health():
    return {
        "service": "processing-service",
        "status": "ok",
    }


@app.post("/analysis")
def analyze_document(
    request: AnalysisRequest,
    authority=Depends(get_processing_authority),
):
    require_action(
        authority,
        "analyze_document",
    )

    if authority.get("resource_id") != request.document_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token is not valid for this resource",
        )

    read_token = create_resource_token(
        action="processing_read_document",
        document_id=request.document_id,
    )

    document = request_resource_service(
        method="GET",
        path=f"/internal/documents/{request.document_id}",
        authority_token=read_token,
    )

    analysis = analyze_text(document["content"])

    store_token = create_resource_token(
        action="store_analysis_result",
        document_id=request.document_id,
    )

    stored_result = request_resource_service(
        method="POST",
        path="/internal/analysis-results",
        authority_token=store_token,
        json_body={
            "document_id": request.document_id,
            "analysis": analysis,
        },
    )

    return {
        "analysis_result_id": stored_result["id"],
        "document_id": document["id"],
        "document_owner": document["owner_id"],
        "analysis": analysis,
    }
