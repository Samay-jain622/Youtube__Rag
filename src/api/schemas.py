"""API request and response schemas."""

from pydantic import BaseModel, Field


class VideoRequest(BaseModel):
    video_id: str = Field(pattern=r"^[A-Za-z0-9_-]{11}$")


class ChatRequest(BaseModel):
    video_id: str = Field(pattern=r"^[A-Za-z0-9_-]{11}$")
    query: str = Field(min_length=1, max_length=4000)
    user_id: str | None = Field(default=None, min_length=1, max_length=128)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=128)


class StatusResponse(BaseModel):
    status: str
    message: str | None = None
    video_id: str | None = None
    response: str | None = None
    job_id: str | None = None
    conversation_id: str | None = None
