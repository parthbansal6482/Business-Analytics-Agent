"""
Qdrant vector store operations.
All 5 collections share vector_size=384, Distance.COSINE.
"""

import os
import uuid
import logging
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams, Distance, PointStruct,
    Filter, FieldCondition, MatchValue, SearchParams,
)

logger = logging.getLogger(__name__)

client = QdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6333"), timeout=30)

COLLECTIONS = {
    "ecomm_catalog":     {"size": 384, "distance": Distance.COSINE},
    "ecomm_reviews":     {"size": 384, "distance": Distance.COSINE},
    "ecomm_pricing":     {"size": 384, "distance": Distance.COSINE},
    "ecomm_competitors": {"size": 384, "distance": Distance.COSINE},
    "ecomm_user_memory": {"size": 384, "distance": Distance.COSINE},
}


def init_collections() -> None:
    """Create all collections if they don't exist."""
    for name, config in COLLECTIONS.items():
        try:
            if not client.collection_exists(name):
                client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(
                        size=config["size"],
                        distance=config["distance"],
                    ),
                )
                logger.info(f"Created Qdrant collection: {name}")
            else:
                logger.info(f"Qdrant collection exists: {name}")
        except Exception as e:
            logger.error(f"Failed to init collection {name}: {e}")


def upsert_chunks(
    collection: str,
    chunks: list[dict],
    vectors: list[list[float]],
    user_id: str,
) -> int:
    """Upsert chunks with their embeddings."""
    if not chunks or not vectors:
        return 0

    points = []
    for chunk, vector in zip(chunks, vectors):
        payload = {
            "user_id": user_id,
            "text": chunk.get("text", ""),
            **{k: v for k, v in chunk.items() if k != "text"},
        }
        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload=payload,
            )
        )

    # Batch upsert in chunks of 100
    batch_size = 100
    for i in range(0, len(points), batch_size):
        client.upsert(collection_name=collection, points=points[i : i + batch_size])

    return len(points)


def search(
    collection: str,
    query_vector: list[float],
    user_id: str,
    top_k: int = 10,
    extra_filter: dict | None = None,
) -> list[dict]:
    """Search a collection, filtered by user_id."""
    try:
        conditions = [FieldCondition(key="user_id", match=MatchValue(value=user_id))]

        results = client.search(
            collection_name=collection,
            query_vector=query_vector,
            query_filter=Filter(must=conditions),
            limit=top_k,
            with_payload=True,
        )
        return [{"text": r.payload.get("text", ""), "score": r.score, **r.payload} for r in results]
    except Exception as e:
        logger.warning(f"Qdrant search failed on {collection}: {e}")
        return []


def delete_by_user(collection: str, user_id: str) -> None:
    """Delete all vectors for a user from a collection."""
    try:
        client.delete(
            collection_name=collection,
            points_selector=Filter(
                must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
            ),
        )
    except Exception as e:
        logger.warning(f"Failed to delete user data from {collection}: {e}")


def get_collection_count(collection: str, user_id: str) -> int:
    """Count documents for a user in a collection."""
    try:
        result = client.count(
            collection_name=collection,
            count_filter=Filter(
                must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
            ),
        )
        return result.count
    except Exception:
        return 0
