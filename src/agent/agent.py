"""Stateless YouTube RAG agent lifecycle."""

from uuid import uuid4

from langchain_qdrant import QdrantVectorStore

from src.agent.executor import route_query, summarize
from src.agent.memory import create_memory
from src.agent.state import create_video, get_video, load_documents, update_video
from src.models.embeddings import embeddings, ensure_collection, qdrant_client
from src.tools.search import build_search_chain
from src.tools.tasks import process_video
from src.utils.config import settings
from src.utils.redis_client import distributed_lock


class VideoNotReadyError(RuntimeError):
    pass


def enqueue_video(video_id: str) -> dict[str, str | None]:
    """Idempotently queue a video for ingestion."""
    with distributed_lock(f"lock:enqueue:{video_id}", timeout=30) as acquired:
        if not acquired:
            return {"video_id": video_id, "status": "processing", "job_id": None}

        record = get_video(video_id)
        if record and record.status == "ready":
            return {
                "video_id": video_id,
                "status": "ready",
                "job_id": record.task_id,
            }
        if record and record.status in {"queued", "processing", "retrying"}:
            return {
                "video_id": video_id,
                "status": record.status,
                "job_id": record.task_id,
            }

        create_video(video_id)
        task_id = str(uuid4())
        update_video(video_id, status="queued", task_id=task_id, error=None)
        try:
            process_video.apply_async(args=[video_id], task_id=task_id)
        except Exception as exc:
            update_video(video_id, status="failed", error=str(exc))
            raise RuntimeError("Unable to queue video processing") from exc

        return {"video_id": video_id, "status": "queued", "job_id": task_id}


def video_status(video_id: str) -> dict[str, str | None]:
    record = get_video(video_id)
    if record is None:
        return {
            "video_id": video_id,
            "status": "not_found",
            "job_id": None,
            "message": None,
        }
    return {
        "video_id": video_id,
        "status": record.status,
        "job_id": record.task_id,
        "message": record.error,
    }


def ask(
    query: str,
    video_id: str,
    user_id: str,
    conversation_id: str,
) -> str:
    """Answer from persistent state so any API replica can handle the request."""
    record = get_video(video_id)
    if record is None or record.status != "ready":
        status = record.status if record else "not_found"
        raise VideoNotReadyError(f"Video is not ready (status: {status})")

    documents = load_documents(video_id)
    if not documents:
        raise VideoNotReadyError("Video transcript chunks are unavailable")

    lock_name = f"lock:conversation:{user_id}:{conversation_id}:{video_id}"
    with distributed_lock(lock_name, timeout=300) as acquired:
        if not acquired:
            raise RuntimeError("Another message is already processing")

        ensure_collection()
        memory = create_memory(video_id, user_id, conversation_id)
        if route_query(query) == "summary":
            response = summarize(documents, query)
        else:
            vectorstore = QdrantVectorStore(
                client=qdrant_client,
                collection_name=settings.qdrant_collection,
                embedding=embeddings,
            )
            chain = build_search_chain(
                vectorstore,
                documents,
                memory,
                video_id,
            )
            response = chain.invoke(query)

        memory.save_context({"input": query}, {"output": response})
        return response
