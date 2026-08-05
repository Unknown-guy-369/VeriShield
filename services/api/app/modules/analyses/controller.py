import json
import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from pydantic import ValidationError
from starlette.datastructures import UploadFile

from app.core.errors import AppError
from app.dependencies import get_analysis_service
from app.modules.analyses.schemas import AnalysisRecord, AnalysisType, CreateAnalysisRequest
from app.modules.analyses.service import AnalysisService

router = APIRouter(prefix="/analyses", tags=["analyses"])
logger = logging.getLogger(__name__)


def validate_payload(payload: Any) -> CreateAnalysisRequest:
    try:
        return CreateAnalysisRequest.model_validate(payload)
    except ValidationError as error:
        messages = [str(item.get("msg", "Invalid request.")) for item in error.errors()]
        raise AppError(400, "VALIDATION_ERROR", " ".join(messages)) from error




@router.post("", response_model=AnalysisRecord, status_code=201)
async def create_analysis(
    request: Request,
    background_tasks: BackgroundTasks,
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisRecord:
    content_type = request.headers.get("content-type", "").lower()
    upload: UploadFile | None = None

    if content_type.startswith("multipart/form-data"):
        form = await request.form(max_files=1, max_fields=10)
        upload_value = form.get("file")
        upload = upload_value if isinstance(upload_value, UploadFile) else None
        payload = {
            "input": form.get("input"),
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

    record = await service.create(validate_payload(payload), upload)

    if record.type in (AnalysisType.IMAGE, AnalysisType.VIDEO):
        from app.dependencies import get_media_forensics_service
        media_service = get_media_forensics_service(request)
        background_tasks.add_task(media_service.process_media, record.id)
        
    logger.info(
        "analysis accepted id=%s type=%s status=%s progress=%s",
        record.id,
        record.type.value,
        record.status.value,
        record.progress,
    )
    background_tasks.add_task(service.process_analysis, record.id)
    logger.info("analysis worker scheduled id=%s worker=text_pipeline", record.id)
    return record


@router.get("/{analysis_id}", response_model=AnalysisRecord)
async def get_analysis(
    analysis_id: UUID,
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisRecord:
    return await service.find_one(analysis_id)


@router.get("/{analysis_id}/media")
async def get_media_forensics(
    analysis_id: UUID,
    request: Request,
) -> Any:
    from app.dependencies import get_media_forensics_service
    service = get_media_forensics_service(request)
    result = await service.forensics_repository.get_result(analysis_id)
    if not result:
        raise AppError(404, "NOT_FOUND", "Media forensics result not found or not completed yet.")
    return result
@router.get("/{analysis_id}/report", response_model=AnalysisRecord)
async def get_analysis_report(
    analysis_id: UUID,
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisRecord:
    report = await service.find_report(analysis_id)
    logger.info(
        "analysis report requested id=%s status=%s progress=%s has_result=%s",
        report.id,
        report.status.value,
        report.progress,
        report.result is not None,
    )
    return report
