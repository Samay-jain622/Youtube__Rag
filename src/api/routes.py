"""YouTube RAG API routes."""

from uuid import uuid4
from hmac import compare_digest

from fastapi import APIRouter, Header, HTTPException, Request, status

from src.agent.agent import (
    VideoNotReadyError,
    ask,
    enqueue_video,
    video_status,
)
from src.api.schemas import ChatRequest, StatusResponse, VideoRequest
from src.utils.config import settings
from src.utils.redis_client import rate_limit

router = APIRouter()


def _authorize(api_key: str | None) -> None:
    if settings.api_access_key and (
        api_key is None or not compare_digest(api_key, settings.api_access_key)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )


def _enforce_rate_limit(request: Request, identity: str) -> None:
    client_host = request.client.host if request.client else "unknown"
    if not rate_limit(f"{client_host}:{identity}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@router.post("/init_video", response_model=StatusResponse)
def initialize_video(
    payload: VideoRequest,
    request: Request,
    x_api_key: str | None = Header(default=None),
) -> StatusResponse:
    _authorize(x_api_key)
    _enforce_rate_limit(request, payload.video_id)
    result = enqueue_video(payload.video_id)
    return StatusResponse(
        status=str(result["status"]),
        video_id=payload.video_id,
        job_id=result.get("job_id"),
    )


@router.get("/videos/{video_id}/status", response_model=StatusResponse)
def get_video_status(
    video_id: str,
    x_api_key: str | None = Header(default=None),
) -> StatusResponse:
    _authorize(x_api_key)
    result = video_status(video_id)
    return StatusResponse(
        status=str(result["status"]),
        video_id=video_id,
        job_id=result.get("job_id"),
        message=result.get("message"),
    )


@router.post("/chat", response_model=StatusResponse)
def chat(
    payload: ChatRequest,
    request: Request,
    x_api_key: str | None = Header(default=None),
) -> StatusResponse:
    _authorize(x_api_key)
    user_id = payload.user_id or (
        f"anonymous:{request.client.host}" if request.client else "anonymous"
    )
    conversation_id = payload.conversation_id or str(uuid4())
    _enforce_rate_limit(request, user_id)
    try:
        response = ask(
            payload.query,
            payload.video_id,
            user_id,
            conversation_id,
        )
    except VideoNotReadyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return StatusResponse(
        status="success",
        response=response,
        conversation_id=conversation_id,
    )
