"""
Schema Mapper: Uses LLM to map user-provided CSV columns to internal field names.
This allows the system to handle "Cost" -> "price", "User Feedback" -> "review_text", etc.
"""

import json
import logging
import re
from utils.llm import call_llm_with_retry

logger = logging.getLogger(__name__)

# The internal canonical names we need
SCHEMA_MAP = {
    "catalog": {
        "required": ["name", "price"],
        "optional": ["category", "sku", "rating", "inventory", "sales_volume"]
    },
    "reviews": {
        "required": ["review_text", "rating"],
        "optional": ["sku", "date", "verified_purchase"]
    },
    "pricing": {
        "required": ["your_price", "competitor_price"],
        "optional": ["sku", "competitor_name", "date"]
    },
    "competitors": {
        "required": ["competitor_name", "price"],
        "optional": ["product_title", "rating", "review_count", "features"]
    },
    "orders": {
        "required": ["order_id", "total_price"],
        "optional": ["date", "status", "line_items", "customer_id"]
    },
    "customers": {
        "required": ["customer_id", "email"],
        "optional": ["total_spent", "orders_count", "state"]
    }
}

def map_columns_with_llm(user_columns: list[str], data_type: str) -> dict[str, str]:
    """
    Returns a mapping of {user_column: internal_column}.
    Only maps columns that actually have a match.
    """
    spec = SCHEMA_MAP.get(data_type)
    if not spec:
        return {}

    prompt = f"""You are a data engineering assistant. Map the user's CSV columns to our internal database fields.

DATA TYPE: {data_type}
INTERNAL FIELDS WE NEED: {spec['required'] + spec['optional']}
USER'S COLUMNS: {user_columns}

RULES:
1. Map "price", "cost", "msrp", "amount" to "price" or "your_price" depending on context.
2. Map "feedback", "comment", "text", "body" to "review_text".
3. Map "score", "stars" to "rating".
4. Map "title", "label", "product" to "name" or "product_title".
5. Return ONLY a JSON object where keys are the USER'S columns and values are the INTERNAL fields.
6. If a column doesn't match anything, skip it.

Example Output: {{"User Cost": "price", "Comments": "review_text"}}
JSON:"""

    try:
        response = call_llm_with_retry(prompt)
        # Find JSON block
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            mapping = json.loads(match.group())
            # Clean: ensure we only return mappings to our allowed internal fields
            allowed = set(spec['required'] + spec['optional'])
            valid_mapping = {k: v for k, v in mapping.items() if v in allowed and k in user_columns}
            logger.info(f"LLM Column Mapping for {data_type}: {valid_mapping}")
            return valid_mapping
    except Exception as e:
        logger.error(f"LLM Column Mapping failed: {e}")
    
    return {}
