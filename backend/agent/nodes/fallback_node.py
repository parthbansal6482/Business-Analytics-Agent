"""
Fallback Node: called when any node sets state["error"].
Assembles a partial report from whatever nodes completed — never returns empty.
"""

import logging
from agent.state import AgentState
from utils.sse import publish_step

logger = logging.getLogger(__name__)


def fallback_node(state: AgentState) -> AgentState:
    session_id = state["session_id"]
    error = state.get("error", "Unknown error")
    completed = state.get("completed_nodes", [])

    logger.error(f"Fallback triggered for session {session_id}. Error: {error}. Completed: {completed}")

    # Build partial report from whatever completed
    exec_summary = (
        f"Partial analysis for: {state['query']}. "
        f"Completed stages: {', '.join(completed) or 'none'}. "
        "Some analysis sections are unavailable due to a processing error."
    )

    sentiment = state.get("sentiment_results", {})
    pricing   = state.get("pricing_results", {})
    competitor = state.get("competitor_results", {})

    partial_report = {
        "executive_summary": exec_summary,
        "mode": state.get("mode", "quick"),
        "key_metrics": {
            "revenue_impact": "Partial data",
            "rating_change": "N/A",
            "price_gap_pct": pricing.get("gap_pct", 0.0),
        },
        "sentiment_breakdown": {
            "positive_pct": sentiment.get("positive_pct", 0),
            "neutral_pct": sentiment.get("neutral_pct", 0),
            "negative_pct": sentiment.get("negative_pct", 0),
            "top_complaints": sentiment.get("top_complaints", []),
            "feature_requests": sentiment.get("feature_requests", []),
        },
        "pricing_analysis": {
            "your_price": pricing.get("your_price", 0.0),
            "competitor_avg": pricing.get("competitor_avg", 0.0),
            "gap_pct": pricing.get("gap_pct", 0.0),
            "recommendation": pricing.get("recommendation", "Pricing data unavailable."),
        },
        "competitive_gaps": competitor.get("gaps", []),
        "root_cause": state.get("business_synthesis", f"Analysis interrupted: {error}"),
        "recommended_actions": [
            {
                "action": "Ensure all data sources are uploaded (catalog, reviews, pricing, competitors)",
                "priority": "High",
                "expected_impact": "Full analysis capability",
            }
        ],
        "confidence_score": 15.0,
        "data_completeness": "Low",
        "cost_usd": 0.0,
        "tokens_used": state.get("total_tokens_used", 0),
        "follow_up_suggestions": [],
        "duration_seconds": 0.0,
        "error": error,
    }

    publish_step(session_id, "report", "done", "Partial report ready")

    return {
        **state,
        "report": partial_report,
        "error": None,  # clear error so app doesn't raise 500
        "completed_nodes": [*completed, "fallback_node"],
    }
