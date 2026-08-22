"""Database-backed video and transcript state."""

import json

from langchain_core.documents import Document
from redis.exceptions import RedisError
from sqlalchemy import delete, select

from src.models.database import session_scope
from src.models.entities import TranscriptChunk, VideoRecord
from src.utils.redis_client import redis_client


def get_video(video_id: str) -> VideoRecord | None:
    with session_scope() as session:
        return session.get(VideoRecord, video_id)


def create_video(video_id: str) -> VideoRecord:
    with session_scope() as session:
        record = session.get(VideoRecord, video_id)
        if record is None:
            record = VideoRecord(video_id=video_id, status="pending")
            session.add(record)
            session.flush()
        return record


def update_video(
    video_id: str,
    *,
    status: str,
    task_id: str | None = None,
    error: str | None = None,
) -> VideoRecord:
    with session_scope() as session:
        record = session.get(VideoRecord, video_id)
        if record is None:
            record = VideoRecord(video_id=video_id)
            session.add(record)
        record.status = status
        record.error = error
        if task_id is not None:
            record.task_id = task_id
        session.flush()
        return record


def replace_documents(video_id: str, documents: list[Document]) -> None:
    with session_scope() as session:
        session.execute(
            delete(TranscriptChunk).where(TranscriptChunk.video_id == video_id)
        )
        session.add_all(
            TranscriptChunk(
                video_id=video_id,
                position=position,
                content=document.page_content,
                start=float(document.metadata.get("start", 0)),
                duration=float(document.metadata.get("duration", 0)),
            )
            for position, document in enumerate(documents)
        )
    cache_payload = [
        {
            "content": document.page_content,
            "metadata": document.metadata,
        }
        for document in documents
    ]
    try:
        redis_client.setex(
            f"documents:{video_id}",
            86400,
            json.dumps(cache_payload),
        )
    except RedisError:
        pass


def load_documents(video_id: str) -> list[Document]:
    try:
        cached = redis_client.get(f"documents:{video_id}")
        if cached:
            return [
                Document(
                    page_content=item["content"],
                    metadata=item["metadata"],
                )
                for item in json.loads(cached)
            ]
    except (RedisError, json.JSONDecodeError, KeyError, TypeError):
        pass

    with session_scope() as session:
        chunks = session.scalars(
            select(TranscriptChunk)
            .where(TranscriptChunk.video_id == video_id)
            .order_by(TranscriptChunk.position)
        ).all()
        documents = [
            Document(
                page_content=chunk.content,
                metadata={
                    "video_id": chunk.video_id,
                    "start": chunk.start,
                    "duration": chunk.duration,
                },
            )
            for chunk in chunks
        ]
    if documents:
        try:
            redis_client.setex(
                f"documents:{video_id}",
                86400,
                json.dumps(
                    [
                        {
                            "content": document.page_content,
                            "metadata": document.metadata,
                        }
                        for document in documents
                    ]
                ),
            )
        except RedisError:
            pass
    return documents
