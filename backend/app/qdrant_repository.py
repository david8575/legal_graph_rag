from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from backend.app.config import settings
from backend.app.models import TextChunk


LEGAL_CHUNKS_COLLECTION = "legal_chunks"
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

def build_chunk_payload(chunk: TextChunk) -> dict:
    return {
        "chunk_id": chunk.id,
        "source_type": chunk.source_type.value,
        "source_id": chunk.source_id,
        "domain": chunk.domain.value,
        "chunk_index": chunk.chunk_index,
        "text": chunk.text,
        **chunk.metadata,
    }

def upsert_chunk_vectors(
    chunks: list[TextChunk],
    vectors: list[list[float]],
) -> dict:
    if len(chunks) != len(vectors):
        raise ValueError("chunks and vectors length mismatch")

    client = get_qdrant_client()
    ensure_legal_chunks_collection(
        vector_size=len(vectors[0]) if vectors else DEFAULT_VECTOR_SIZE,
    )

    points = [
        PointStruct(
            id=qdrant_point_id(chunk),
            vector=vector,
            payload=build_chunk_payload(chunk),
        )
        for chunk, vector in zip(chunks, vectors)
    ]

    if points:
        client.upsert(
            collection_name=LEGAL_CHUNKS_COLLECTION,
            points=points,
        )

    return {
        "collection": LEGAL_CHUNKS_COLLECTION,
        "points_count": len(points),
    }

def qdrant_point_id(chunk: TextChunk) -> str:
    return str(uuid5(NAMESPACE_URL, chunk.id))

def search_similar_chunks(
    query_vector: list[float],
    limit: int = 5,) -> list[dict]: 
    client = get_qdrant_client()
    
    result = client.query_points(
        collection_name=LEGAL_CHUNKS_COLLECTION,
        query=query_vector,
        limit=limit,
        with_payload=True,
    )

    return [
        {
            "id": str(point.id),
            "score": point.score,
            "payload": point.payload,
        }
        for point in result.points
    ]