"""
Global Stats Aggregator: scrolls the full dataset for a user (up to 2000 rows)
to calculate true averages and totals before LLM analysis.
This solves the "complete data" analysis problem.
"""

import logging
import pandas as pd
from agent.state import AgentState
from memory.qdrant_store import client as qdrant_client
from qdrant_client.models import Filter, FieldCondition, MatchValue
from utils.sse import publish_step

logger = logging.getLogger(__name__)

def _fetch_all_payloads(collection: str, user_id: str) -> list[dict]:
    """Scroll through up to 2000 points in a collection for a specific user."""
    all_payloads = []
    next_page = None
    
    try:
        # We cap at 2000 total points for performance
        while len(all_payloads) < 2000:
            results, next_page = qdrant_client.scroll(
                collection_name=collection,
                scroll_filter=Filter(
                    must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
                ),
                limit=500,
                offset=next_page,
                with_payload=True,
                with_vectors=False,
            )
            all_payloads.extend([r.payload for r in results])
            if not next_page:
                break
    except Exception as e:
        logger.warning(f"Failed to scroll {collection}: {e}")
        
    return all_payloads

def global_stats_aggregator(state: AgentState) -> AgentState:
    user_id = state["user_id"]
    session_id = state["session_id"]
    
    publish_step(session_id, "analyze", "in_progress", "Calculating global statistics across your entire dataset...")
    
    stats = {
        "catalog": {"total_products": 0, "avg_price": 0.0, "avg_rating": 0.0, "total_inventory": 0},
        "reviews": {"total_reviews": 0, "avg_rating": 0.0},
        "pricing": {"avg_your_price": 0.0, "avg_competitor_price": 0.0, "global_price_gap_pct": 0.0},
        "orders":  {"total_orders": 0, "total_revenue": 0.0},
    }
    
    # 1. Catalog Stats
    catalog_data = _fetch_all_payloads("ecomm_catalog", user_id)
    if catalog_data:
        df = pd.DataFrame(catalog_data)
        stats["catalog"]["total_products"] = len(df)
        if "price" in df.columns:
            stats["catalog"]["avg_price"] = float(pd.to_numeric(df["price"], errors='coerce').mean() or 0.0)
        if "rating" in df.columns:
            stats["catalog"]["avg_rating"] = float(pd.to_numeric(df["rating"], errors='coerce').mean() or 0.0)
        if "inventory" in df.columns:
            stats["catalog"]["total_inventory"] = int(pd.to_numeric(df["inventory"], errors='coerce').sum() or 0)

    # 2. Review Stats
    review_data = _fetch_all_payloads("ecomm_reviews", user_id)
    if review_data:
        df = pd.DataFrame(review_data)
        stats["reviews"]["total_reviews"] = len(df)
        if "rating" in df.columns:
            stats["reviews"]["avg_rating"] = float(pd.to_numeric(df["rating"], errors='coerce').mean() or 0.0)

    # 3. Pricing Stats
    pricing_data = _fetch_all_payloads("ecomm_pricing", user_id)
    if pricing_data:
        df = pd.DataFrame(pricing_data)
        if "your_price" in df.columns and "competitor_price" in df.columns:
            y = pd.to_numeric(df["your_price"], errors='coerce').mean() or 0.0
            c = pd.to_numeric(df["competitor_price"], errors='coerce').mean() or 0.0
            stats["pricing"]["avg_your_price"] = float(y)
            stats["pricing"]["avg_competitor_price"] = float(c)
            if c > 0:
                stats["pricing"]["global_price_gap_pct"] = float(((y - c) / c) * 100)

    # 4. Order Stats
    order_data = _fetch_all_payloads("ecomm_orders", user_id)
    if order_data:
        df = pd.DataFrame(order_data)
        stats["orders"]["total_orders"] = len(df)
        if "total_price" in df.columns:
            stats["orders"]["total_revenue"] = float(pd.to_numeric(df["total_price"], errors='coerce').sum() or 0.0)

    logger.info(f"Global Stats calculated for user {user_id}: {stats}")
    
    return {
        **state,
        "global_stats": stats,
        "completed_nodes": [*state.get("completed_nodes", []), "global_stats_aggregator"]
    }
