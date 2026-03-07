"""
Full data ingestion pipeline: parse → validate → chunk → embed → upsert.
Re-uploading a file REPLACES the previous data for that user+collection
(delete-before-upsert ensures no stale data accumulates in Qdrant).
"""

import io
import os
import logging
import pandas as pd
from data.chunker import chunk_dataframe
from data.embedder import embed
from memory.qdrant_store import upsert_chunks, delete_by_user

logger = logging.getLogger(__name__)

# Set to False to skip the delete step (useful for debugging / append mode)
DELETE_BEFORE_UPLOAD = os.getenv("DELETE_BEFORE_UPLOAD", "true").lower() == "true"

# Expected columns per data type (required)
REQUIRED_COLUMNS = {
    "catalog":     {"name", "price"},
    "reviews":     {"review_text", "rating"},
    "pricing":     {"your_price", "competitor_price"},
    "competitors": {"competitor_name", "price"},
    "orders":      {"order_id", "total_price"},
    "customers":   {"customer_id", "email"},
}

# Optional columns per type
OPTIONAL_COLUMNS = {
    "catalog":     {"category", "sku", "rating", "inventory", "sales_volume"},
    "reviews":     {"sku", "date", "verified_purchase"},
    "pricing":     {"sku", "competitor_name", "date"},
    "competitors": {"product_title", "rating", "review_count", "features"},
    "orders":      {"date", "status", "line_items", "customer_id"},
    "customers":   {"total_spent", "orders_count", "state"},
}


def validate_schema(df: pd.DataFrame, data_type: str) -> None:
    """Check that required columns are present (case-insensitive)."""
    df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
    required = REQUIRED_COLUMNS.get(data_type, set())
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"Data type '{data_type}' is missing required columns: {missing}. "
            f"Found: {list(df.columns)}"
        )


def ingest_file(
    file_bytes: bytes,
    filename: str,
    data_type: str,
    user_id: str,
) -> dict:
    """
    Full pipeline: parse → validate → clean → chunk → embed → upsert.
    Old data for this user+collection is deleted before upserting to prevent
    stale data from lingering in Qdrant.
    Returns {"rows_loaded": N, "data_type": data_type}
    """
    # 1. Parse
    fname = filename.lower()
    if fname.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(file_bytes))
    elif fname.endswith(".xlsx") or fname.endswith(".xls"):
        df = pd.read_excel(io.BytesIO(file_bytes))
    elif fname.endswith(".json"):
        df = pd.read_json(io.BytesIO(file_bytes))
    else:
        raise ValueError(f"Unsupported file format: {filename}")

    # 2. Normalize column names
    df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]

    # 3. Validate
    validate_schema(df, data_type)

    # 4. Clean
    df = df.dropna(how="all").fillna("")
    df = df.head(2000)  # safety cap: no OOM on huge files

    # 5. Chunk
    chunks = chunk_dataframe(df, data_type)

    # 6. Embed
    texts = [c["text"] for c in chunks]
    vectors = embed(texts)

    # 7. Delete old data for this user+collection BEFORE upserting
    collection = f"ecomm_{data_type}"
    if DELETE_BEFORE_UPLOAD:
        logger.info(f"Deleting existing data for user={user_id} in {collection} before re-upload")
        delete_by_user(collection, user_id)

    # 8. Upsert fresh data
    count = upsert_chunks(collection, chunks, vectors, user_id)
    logger.info(f"Upserted {count} chunks to {collection} for user {user_id}")

    return {"rows_loaded": len(df), "data_type": data_type}
