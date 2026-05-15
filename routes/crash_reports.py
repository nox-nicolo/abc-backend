import logging
from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field


crash_reports = APIRouter(prefix="/crash-reports", tags=["Crash Reports"])
logger = logging.getLogger("abc.crash_reports")


class CrashReportPayload(BaseModel):
    message: str = Field(..., max_length=1000)
    error: str = Field(..., max_length=8000)
    stack_trace: Optional[str] = Field(None, max_length=30000)
    context: Optional[str] = Field(None, max_length=1000)
    platform: Optional[str] = Field(None, max_length=80)
    app_version: Optional[str] = Field(None, max_length=80)
    build_number: Optional[str] = Field(None, max_length=80)
    fatal: bool = False


@crash_reports.post("", status_code=202)
def create_crash_report(payload: CrashReportPayload, request: Request):
    request_id = getattr(request.state, "request_id", None)
    logger.error(
        "Client crash report",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "status_code": 202,
            "client_host": request.client.host if request.client else None,
            "crash_message": payload.message,
            "crash_error": payload.error,
            "crash_context": payload.context,
            "crash_platform": payload.platform,
            "app_version": payload.app_version,
            "build_number": payload.build_number,
            "fatal": payload.fatal,
        },
    )
    if payload.stack_trace:
        logger.error("Client crash stack trace\n%s", payload.stack_trace)
    return {"accepted": True, "request_id": request_id}
