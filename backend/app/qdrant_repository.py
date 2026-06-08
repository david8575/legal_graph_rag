from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from backend.app.config import settings


LEGAL_CHUNKS_COLLECTION = "legal_chunks"

# bge-m3 embedding dimension is 1024.
# If the embedding model changes, this value may also need to change.
DEFAULT_VECTOR_SIZE = 1024


def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url)


def ensure_legal_chunks_collection(
    vector_size: int = DEFAULT_VECTOR_SIZE,
) -> dict:
    client = get_qdrant_client()

    if client.collection_exists(LEGAL_CHUNKS_COLLECTION):
        return {
            "collection": LEGAL_CHUNKS_COLLECTION,
            "status": "exists",
            "vector_size": vector_size,
        }

    client.create_collection(
        collection_name=LEGAL_CHUNKS_COLLECTION,
        vectors_config=VectorParams(
            size=vector_size,
            distance=Distance.COSINE,
        ),
    )

    return {
        "collection": LEGAL_CHUNKS_COLLECTION,
        "status": "created",
        "vector_size": vector_size,
    }