"""
AgentState: the shared state TypedDict that flows through all LangGraph nodes.
"""

from typing import TypedDict, Literal


class AgentState(TypedDict):
    session_id: str
    user_id: str
    query: str
    mode: Literal["quick", "deep"]

    # Memory
    user_preferences: dict
    past_analyses: list[str]

    # Retrieved data chunks (text strings)
    catalog_chunks: list[str]
    review_chunks: list[str]
    pricing_chunks: list[str]
    competitor_chunks: list[str]
    order_chunks: list[str]
    customer_chunks: list[str]

    # Database metric counts
    total_products_synced: int
    total_orders_synced: int
    total_customers_synced: int

    # Analysis outputs
    sentiment_results: dict
    pricing_results: dict
    competitor_results: dict

    # High-level synthesis
    business_synthesis: str

    # Final report
    report: dict

    # Scoring
    confidence_score: float
    data_completeness: str        # "High" | "Moderate" | "Low"

    # Cost tracking
    total_tokens_used: int
    estimated_cost_usd: float     # Always 0.0

    # Control flow
    needs_clarification: bool
    clarification_question: str
    completed_nodes: list[str]
    error: str | None
    is_simple: bool
