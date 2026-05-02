"""
Full data ingestion pipeline: parse → map columns → validate → chunk → embed → upsert.
Re-uploading a file REPLACES the previous data for that user+collection.
"""

import io
import os
import logging
import pandas as pd
from data.chunker import chunk_dataframe
from data.embedder import embed
from data.schema_mapper import map_columns_with_llm
from memory.qdrant_store import upsert_chunks, delete_by_user

logger = logging.getLogger(__name__)

# Set to False to skip the delete step
DELETE_BEFORE_UPLOAD = os.getenv("DELETE_BEFORE_UPLOAD", "true").lower() == "true"

# Canonical internal column names
REQUIRED_COLUMNS = {
    "catalog":     {"name", "price"},
    "reviews":     {"review_text", "rating"},
    "pricing":     {"your_price", "competitor_price"},
    "competitors": {"competitor_name", "price"},
    "orders":      {"order_id", "total_price"},
    "customers":   {"customer_id", "email"},
}

OPTIONAL_COLUMNS = {
    "catalog":     {"category", "sku", "rating", "inventory", "sales_volume"},
    "reviews":     {"sku", "date", "verified_purchase"},
    "pricing":     {"sku", "competitor_name", "date"},
    "competitors": {"product_title", "rating", "review_count", "features"},
    "orders":      {"date", "status", "line_items", "customer_id"},
    "customers":   {"total_spent", "orders_count", "state"},
}

def validate_schema(df: pd.DataFrame, data_type: str) -> None:
    """Check that required columns are present. Uses LLM to map if they are missing."""
    # 1. Normalize current columns for initial check
    df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
    
    required = REQUIRED_COLUMNS.get(data_type, set())
    current_cols = set(df.columns)
    
    # 2. If required columns are missing, try AI-based mapping
    if not (required <= current_cols):
        logger.info(f"Required columns {required} missing in {current_cols}. Attempting AI mapping...")
        mapping = map_columns_with_llm(list(df.columns), data_type)
        if mapping:
            df.rename(columns=mapping, inplace=True)
            # Re-normalize after renaming
            df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
            current_cols = set(df.columns)

    # 3. Final validation
    missing = required - current_cols
    if missing:
        raise ValueError(
            f"Missing required columns: {missing}. Found: {list(df.columns)}. "
            f"Tip: Ensure your file has headers like {list(required)}."
        )

def ingest_file(
    file_bytes: bytes,
    filename: str,
    data_type: str,
    user_id: str,
) -> dict:
    """
    Full pipeline: parse → AI map → validate → clean → chunk → embed → upsert.
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

    # 2. Map & Validate
    validate_schema(df, data_type)

    # 3. Clean
    df = df.dropna(how="all").fillna("")
    df = df.head(2000)  # safety cap

    # 4. Chunk
    chunks = chunk_dataframe(df, data_type)

    # 5. Embed
    texts = [c["text"] for c in chunks]
    vectors = embed(texts)

    # 6. Delete old data
    collection = f"ecomm_{data_type}"
    if DELETE_BEFORE_UPLOAD:
        logger.info(f"Deleting existing data for user={user_id} in {collection}")
        delete_by_user(collection, user_id)

    # 7. Upsert
    count = upsert_chunks(collection, chunks, vectors, user_id)
    return {"rows_loaded": len(df), "data_type": data_type}
