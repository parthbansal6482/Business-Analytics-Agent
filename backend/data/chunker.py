"""
Data chunker: converts a DataFrame row into a text chunk for embedding.
"""

import pandas as pd


def chunk_dataframe(df: pd.DataFrame, data_type: str) -> list[dict]:
    """Convert DataFrame rows to text chunks with metadata."""
    chunks = []

    for _, row in df.iterrows():
        row_dict = row.to_dict()

        if data_type == "catalog":
            text = (
                f"Product: {row_dict.get('name', '')}. "
                f"SKU: {row_dict.get('sku', '')}. "
                f"Category: {row_dict.get('category', '')}. "
                f"Price: {row_dict.get('price', '')}. "
                f"Rating: {row_dict.get('rating', '')}. "
                f"Inventory: {row_dict.get('inventory', '')}. "
                f"Sales Volume: {row_dict.get('sales_volume', '')}."
            )
        elif data_type == "reviews":
            text = (
                f"SKU: {row_dict.get('sku', '')}. "
                f"Rating: {row_dict.get('rating', '')}/5. "
                f"Review: {row_dict.get('review_text', '')}. "
                f"Date: {row_dict.get('date', '')}. "
                f"Verified: {row_dict.get('verified_purchase', '')}."
            )
        elif data_type == "pricing":
            text = (
                f"SKU: {row_dict.get('sku', '')}. "
                f"Your Price: {row_dict.get('your_price', '')}. "
                f"Competitor: {row_dict.get('competitor_name', '')} "
                f"at {row_dict.get('competitor_price', '')}. "
                f"Date: {row_dict.get('date', '')}."
            )
        elif data_type == "competitors":
            text = (
                f"Competitor: {row_dict.get('competitor_name', '')}. "
                f"Product: {row_dict.get('product_title', '')}. "
                f"Price: {row_dict.get('price', '')}. "
                f"Rating: {row_dict.get('rating', '')}. "
                f"Reviews: {row_dict.get('review_count', '')}. "
                f"Features: {row_dict.get('features', '')}."
            )
        else:
            text = " | ".join(f"{k}: {v}" for k, v in row_dict.items())

        chunks.append({"text": text, "data_type": data_type, **row_dict})

    return chunks
