"""Embedding and vector-database clients."""

from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import Distance, PayloadSchemaType, VectorParams

from src.utils.config import settings

if not settings.qdrant_url:
    raise RuntimeError("QDRANT_URL must be set in .env")

embeddings = OpenAIEmbeddings(model=settings.embedding_model)
qdrant_client = QdrantClient(
    url=settings.qdrant_url,
    api_key=settings.qdrant_api_key,
    timeout=10,
)


def ensure_collection() -> None:
    if not qdrant_client.collection_exists(settings.qdrant_collection):
        try:
            qdrant_client.create_collection(
                collection_name=settings.qdrant_collection,
                vectors_config=VectorParams(
                    size=settings.embedding_size,
                    distance=Distance.COSINE,
                ),
            )
            qdrant_client.create_payload_index(
                collection_name=settings.qdrant_collection,
                field_name="metadata.video_id",
                field_schema=PayloadSchemaType.KEYWORD,
            )
        except UnexpectedResponse:
            if not qdrant_client.collection_exists(settings.qdrant_collection):
                raise
