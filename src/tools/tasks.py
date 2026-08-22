"""Background video-ingestion tasks."""

from uuid import NAMESPACE_URL, uuid5

from langchain_qdrant import QdrantVectorStore
from qdrant_client.http.models import FieldCondition, Filter, FilterSelector, MatchValue

from src.agent.state import replace_documents, update_video
from src.models.database import initialize_database
from src.models.embeddings import embeddings, ensure_collection, qdrant_client
from src.tools.transcript import fetch_and_chunk
from src.utils.config import settings
from src.utils.redis_client import distributed_lock
from src.worker import celery_app


@celery_app.task(bind=True, max_retries=3, name="videos.process")
def process_video(self, video_id: str) -> dict[str, str]:
    initialize_database()
    with distributed_lock(f"lock:video:{video_id}", timeout=1800) as acquired:
        if not acquired:
            return {"video_id": video_id, "status": "already_processing"}

        try:
            update_video(video_id, status="processing", error=None)
            documents = fetch_and_chunk(video_id)
            final_timestamp = max(
                document.metadata.get("start", 0)
                + document.metadata.get("duration", 0)
                for document in documents
            )
            if final_timestamp > settings.max_video_duration_seconds:
                raise ValueError("Video exceeds the configured duration limit")

            replace_documents(video_id, documents)
            ensure_collection()
            video_filter = Filter(
                must=[
                    FieldCondition(
                        key="metadata.video_id",
                        match=MatchValue(value=video_id),
                    )
                ]
            )
            qdrant_client.delete(
                collection_name=settings.qdrant_collection,
                points_selector=FilterSelector(filter=video_filter),
                wait=True,
            )
            vectorstore = QdrantVectorStore(
                client=qdrant_client,
                collection_name=settings.qdrant_collection,
                embedding=embeddings,
            )
            vectorstore.add_documents(
                documents,
                ids=[
                    str(uuid5(NAMESPACE_URL, f"youtube:{video_id}:{position}"))
                    for position in range(len(documents))
                ],
            )
            update_video(video_id, status="ready", error=None)
            return {"video_id": video_id, "status": "ready"}
        except Exception as exc:
            if self.request.retries < self.max_retries:
                update_video(video_id, status="retrying", error=str(exc))
                raise self.retry(exc=exc, countdown=2 ** (self.request.retries + 1))
            update_video(video_id, status="failed", error=str(exc))
            return {"video_id": video_id, "status": "failed", "error": str(exc)}
