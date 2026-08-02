import json
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import ValidationError
from starlette.datastructures import UploadFile

from app.core.errors import AppError
from app.dependencies import get_analysis_service
from app.modules.analyses.schemas import AnalysisRecord, CreateAnalysisRequest
from app.modules.analyses.service import AnalysisService

router = APIRouter(prefix="/analyses", tags=["analyses"])


def validate_payload(payload: Any) -> CreateAnalysisRequest:
    try:
        return CreateAnalysisRequest.model_validate(payload)
    except ValidationError as error:
        messages = [str(item.get("msg", "Invalid request.")) for item in error.errors()]
        raise AppError(400, "VALIDATION_ERROR", " ".join(messages)) from error


@router.post("", response_model=AnalysisRecord, status_code=201)
async def create_analysis(
    request: Request,
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisRecord:
    content_type = request.headers.get("content-type", "").lower()
    upload: UploadFile | None = None

    if content_type.startswith("multipart/form-data"):
        form = await request.form(max_files=1, max_fields=10)
        upload_value = form.get("file")
        upload = upload_value if isinstance(upload_value, UploadFile) else None
        payload = {
            "type": form.get("type"),
            "preferredLanguage": form.get("preferredLanguage", "en"),
        }
    elif content_type.startswith("application/json"):
        content_length = int(request.headers.get("content-length", "0") or 0)
        max_json_bytes = service.settings.json_body_limit_mb * 1024 * 1024
        if content_length > max_json_bytes:
            raise AppError(413, "PAYLOAD_TOO_LARGE", "The JSON request body is too large.")
        try:
            payload = await request.json()
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise AppError(400, "INVALID_JSON", "The request body is not valid JSON.") from error
    else:
        raise AppError(
            415,
            "UNSUPPORTED_CONTENT_TYPE",
            "Use application/json or multipart/form-data.",
        )

    return await service.create(validate_payload(payload), upload)


@router.get("/{analysis_id}", response_model=AnalysisRecord)
async def get_analysis(
    analysis_id: UUID,
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisRecord:
    return await service.find_one(analysis_id)
