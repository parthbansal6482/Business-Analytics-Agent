"""
Report Generator: produces the final structured JSON report validated with Pydantic.
Saves to PostgreSQL and emits final SSE event.
"""

import json
import logging
import time
from typing import Optional
from pydantic import BaseModel
from agent.state import AgentState
from utils.llm import call_llm_with_retry, count_tokens
from utils.sse import publish_step
from utils.confidence import calculate_confidence, get_data_completeness
from utils.cost_tracker import get_session_cost

logger = logging.getLogger(__name__)


class ActionItem(BaseModel):
    action: str
    priority: str
    expected_impact: str


class SentimentBreakdown(BaseModel):
    positive_pct: int = 0
    neutral_pct: int = 0
    negative_pct: int = 0
    top_complaints: list[str] = []
    feature_requests: list[str] = []


class PricingAnalysis(BaseModel):
    your_price: float = 0.0
    competitor_avg: float = 0.0
    gap_pct: float = 0.0
    recommendation: str = ""


class ResearchReport(BaseModel):
    executive_summary: str
    mode: str
    key_metrics: dict
    sentiment_breakdown: SentimentBreakdown
    pricing_analysis: PricingAnalysis
    competitive_gaps: list[str]
    root_cause: str
    recommended_actions: list[ActionItem]
    confidence_score: float
    data_completeness: str
    cost_usd: float
    tokens_used: int
    follow_up_suggestions: list[str]
    duration_seconds: float
    is_simple: bool = False


def _make_simple_report(state: AgentState) -> tuple[str, int]:
    """Extremely fast path for simple data lookups."""
    # Combine some raw chunks just in case it needs context, but keep it tight
    catalog_text = "\n".join(state.get("catalog_chunks", [])[:3])
    pricing_text = "\n".join(state.get("pricing_chunks", [])[:3])
    review_text  = "\n".join(state.get("review_chunks", [])[:3])
    order_text   = "\n".join(state.get("order_chunks", [])[:3])
    customer_text = "\n".join(state.get("customer_chunks", [])[:3])
    
    prompt = f"""You are a helpful e-commerce assistant. Answer the user's simple question directly.
    
Query: "{state['query']}"

Actual Database Metrics (Total Synced Records):
- Total Products: {state.get('total_products_synced', 'Unknown')}
- Total Orders: {state.get('total_orders_synced', 'Unknown')}
- Total Customers: {state.get('total_customers_synced', 'Unknown')}

Available Data Context (Recent/Relevant Samples - DO NOT COUNT THESE FOR TOTALS):
Catalog: {catalog_text}
Pricing: {pricing_text}
Reviews: {review_text}
Orders: {order_text}
Customers: {customer_text}

CRITICAL: If the user asks for a total count (e.g. "how many products", "total customers"), YOU MUST use the 'Actual Database Metrics' above. DO NOT count the samples listed in 'Available Data Context'.

Respond with valid JSON exactly matching this schema (no markdown fences):
{{
  "executive_summary": "<A direct, 1-2 sentence answer to the user's question.>",
  "key_metrics": {{"revenue_impact": "N/A", "rating_change": "N/A", "price_gap_pct": 0.0}},
  "sentiment_breakdown": {{"positive_pct": 0, "neutral_pct": 0, "negative_pct": 0, "top_complaints": [], "feature_requests": []}},
  "pricing_analysis": {{"your_price": 0.0, "competitor_avg": 0.0, "gap_pct": 0.0, "recommendation": ""}},
  "competitive_gaps": [],
  "root_cause": "",
  "recommended_actions": [],
  "follow_up_suggestions": []
}}"""
    response = call_llm_with_retry(prompt)
    return response, count_tokens(prompt) + count_tokens(response)


def _make_quick_report(state: AgentState, start_time: float) -> dict:
    """Quick mode: minimal Gemini calls, focused on top insights."""
    catalog_text = "\n".join(state.get("catalog_chunks", [])[:5])
    pricing_text = "\n".join(state.get("pricing_chunks", [])[:5])
    review_text  = "\n".join(state.get("review_chunks", [])[:5])
    order_text   = "\n".join(state.get("order_chunks", [])[:5])
    customer_text = "\n".join(state.get("customer_chunks", [])[:5])

    prompt = f"""You are a senior e-commerce analyst. Give a quick business intelligence report.

Query: "{state['query']}"
User preferences: {state.get('user_preferences', {})}

Actual Database Metrics (Total Synced Records):
- Total Products: {state.get('total_products_synced', 'Unknown')}
- Total Orders: {state.get('total_orders_synced', 'Unknown')}
- Total Customers: {state.get('total_customers_synced', 'Unknown')}

CRITICAL INSTRUCTION: If the user asks for total counts, ALWAYS use the 'Actual Database Metrics'. The data below are just small samples and do not represent the total dataset.

Product data (Sample):
{catalog_text}

Pricing data:
{pricing_text}

Review samples:
{review_text}

Order history:
{order_text}

Customer activity:
{customer_text}

Past context: {state.get('past_analyses', [])}
IMPORTANT: If "Past context" is non-empty and the query is generic (e.g., "what should I focus on next"),
explicitly reference at least one concrete past topic in executive_summary.

Respond with valid JSON exactly matching this schema (no markdown fences):
{{
  "executive_summary": "<3-4 sentence business summary with specific findings>",
  "key_metrics": {{
    "revenue_impact": "<e.g. -22% Sales or +15% GMV>",
    "rating_change": "<e.g. +0.3 Stars or -0.5 Stars>",
    "price_gap_pct": <float>
  }},
  "sentiment_breakdown": {{
    "positive_pct": <int>, "neutral_pct": <int>, "negative_pct": <int>,
    "top_complaints": ["<complaint 1>", "<complaint 2>", "<complaint 3>"],
    "feature_requests": ["<request 1>", "<request 2>"]
  }},
  "pricing_analysis": {{
    "your_price": <float>, "competitor_avg": <float>, "gap_pct": <float>,
    "recommendation": "<1-2 sentence actionable recommendation>"
  }},
  "competitive_gaps": ["<gap 1>", "<gap 2>", "<gap 3>"],
  "root_cause": "<3-4 sentence root cause connecting multiple signals with numbers>",
  "recommended_actions": [
    {{"action": "<actionable step>", "priority": "High", "expected_impact": "<metric improvement>"}},
    {{"action": "<actionable step>", "priority": "Medium", "expected_impact": "<metric improvement>"}},
    {{"action": "<actionable step>", "priority": "Low", "expected_impact": "<metric improvement>"}}
  ],
  "follow_up_suggestions": [
    "<follow-up question 1>",
    "<follow-up question 2>",
    "<follow-up question 3>"
  ]
}}"""

    response = call_llm_with_retry(prompt)
    return response, count_tokens(prompt) + count_tokens(response)


def _make_deep_report(state: AgentState) -> dict:
    """Deep mode: uses pre-computed analysis results from other nodes."""
    synthesis = state.get("business_synthesis", "")
    sentiment = state.get("sentiment_results", {})
    pricing   = state.get("pricing_results", {})
    competitor = state.get("competitor_results", {})
    order_text   = "\n".join(state.get("order_chunks", [])[:5])
    customer_text = "\n".join(state.get("customer_chunks", [])[:5])

    prompt = f"""You are a senior e-commerce analyst. Generate a comprehensive intelligence report.

Query: "{state['query']}"
User preferences: {state.get('user_preferences', {})}

Actual Database Metrics (Total Synced Records):
- Total Products: {state.get('total_products_synced', 'Unknown')}
- Total Orders: {state.get('total_orders_synced', 'Unknown')}
- Total Customers: {state.get('total_customers_synced', 'Unknown')}

BUSINESS SYNTHESIS (root cause):
{synthesis}

SENTIMENT DATA: {json.dumps(sentiment)}
PRICING DATA: {json.dumps(pricing)}
COMPETITOR DATA: {json.dumps(competitor)}
CRITICAL INSTRUCTION: If the user asks for total counts, ALWAYS use the 'Actual Database Metrics'. The signals below are just small samples and do not represent the total dataset.

ORDER SIGNALS: {order_text}
CUSTOMER SIGNALS: {customer_text}

Respond with valid JSON exactly matching this schema (no markdown fences):
{{
  "executive_summary": "<4-5 sentence comprehensive business overview with specific metrics>",
  "key_metrics": {{
    "revenue_impact": "<e.g. -22% Sales>",
    "rating_change": "<e.g. +0.3 Stars>",
    "price_gap_pct": <float from pricing data>
  }},
  "sentiment_breakdown": {{
    "positive_pct": <from sentiment data>, "neutral_pct": <int>, "negative_pct": <int>,
    "top_complaints": <from sentiment data>,
    "feature_requests": <from sentiment data>
  }},
  "pricing_analysis": {{
    "your_price": <from pricing data>, "competitor_avg": <from pricing data>,
    "gap_pct": <from pricing data>,
    "recommendation": "<specific recommendation with numbers>"
  }},
  "competitive_gaps": <from competitor data gaps list>,
  "root_cause": "<use the business synthesis above verbatim or refine it>",
  "recommended_actions": [
    {{"action": "<high-priority action>", "priority": "High", "expected_impact": "<metric>"}},
    {{"action": "<medium-priority action>", "priority": "Medium", "expected_impact": "<metric>"}},
    {{"action": "<medium-priority action>", "priority": "Medium", "expected_impact": "<metric>"}},
    {{"action": "<low-priority action>", "priority": "Low", "expected_impact": "<metric>"}}
  ],
  "follow_up_suggestions": [
    "<follow-up research question 1>",
    "<follow-up research question 2>",
    "<follow-up research question 3>"
  ]
}}"""

    response = call_llm_with_retry(prompt)
    return response, count_tokens(prompt) + count_tokens(response)


def report_generator(state: AgentState) -> AgentState:
    start_time = time.time()
    session_id = state["session_id"]

    try:
        mode = state.get("mode", "quick")
        is_simple = state.get("is_simple", False)

        if is_simple:
            raw, tokens = _make_simple_report(state)
        elif mode == "deep":
            raw, tokens = _make_deep_report(state)
        else:
            raw, tokens = _make_quick_report(state, start_time)

        # Parse JSON
        try:
            clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            report_dict = json.loads(clean)
        except json.JSONDecodeError as e:
            logger.error(f"report_generator JSON parse error: {e}\nRaw: {raw[:500]}")
            raise ValueError(f"Report JSON parse failed: {e}")

        duration = round(time.time() - start_time, 1)
        total_tokens = state.get("total_tokens_used", 0) + tokens

        # Add computed fields
        report_dict["mode"] = mode
        report_dict["confidence_score"] = calculate_confidence(state) * 100
        report_dict["data_completeness"] = get_data_completeness(state)
        report_dict["cost_usd"] = get_session_cost(total_tokens)
        report_dict["tokens_used"] = total_tokens
        report_dict["duration_seconds"] = duration
        report_dict["is_simple"] = is_simple

        # Ensure prior memory context is surfaced in generic follow-up queries.
        past = state.get("past_analyses", []) or []
        if past:
            summary = str(report_dict.get("executive_summary", ""))
            lower_summary = summary.lower()
            key_markers = ["bluetooth speaker", "margin", "margins", "pricing", "complaint"]
            has_context_ref = any(m in lower_summary for m in key_markers)
            query_lower = str(state.get("query", "")).lower()
            generic_follow_up = "focus on next" in query_lower or "next" == query_lower.strip()
            if generic_follow_up or not has_context_ref:
                chosen = str(past[0])
                for entry in past:
                    entry_text = str(entry)
                    if any(m in entry_text.lower() for m in key_markers):
                        chosen = entry_text
                        break
                # Use a short snippet so summary remains readable.
                snippet = chosen[:180].replace("\n", " ")
                report_dict["executive_summary"] = (
                    f"{summary} Prior context considered: {snippet}"
                ).strip()

        # Normalize common LLM shape drift before strict validation.
        actions = report_dict.get("recommended_actions")
        if isinstance(actions, list):
            normalized_actions = []
            for a in actions:
                if isinstance(a, dict):
                    normalized_actions.append({
                        "action": str(a.get("action", "")),
                        "priority": a.get("priority", "Medium"),
                        "expected_impact": str(a.get("expected_impact", "")),
                    })
                elif isinstance(a, str):
                    normalized_actions.append({
                        "action": a,
                        "priority": "Medium",
                        "expected_impact": "TBD",
                    })
            report_dict["recommended_actions"] = normalized_actions

        follow_ups = report_dict.get("follow_up_suggestions")
        if isinstance(follow_ups, list):
            report_dict["follow_up_suggestions"] = [str(x) for x in follow_ups]

        # Validate with Pydantic
        validated = ResearchReport(**report_dict)
        report_out = validated.model_dump()

        publish_step(session_id, "report", "done", "Report ready")

        return {
            **state,
            "report": report_out,
            "total_tokens_used": total_tokens,
            "estimated_cost_usd": 0.0,
            "confidence_score": report_out["confidence_score"],
            "data_completeness": report_out["data_completeness"],
            "completed_nodes": [*state.get("completed_nodes", []), "report_generator"],
        }

    except Exception as e:
        logger.error(f"report_generator error: {e}")

        # Fallback partial report
        duration = round(time.time() - start_time, 1)
        partial = {
            "executive_summary": f"Partial analysis completed for: {state['query']}. Some data signals could not be fully processed.",
            "mode": state.get("mode", "quick"),
            "key_metrics": {"revenue_impact": "N/A", "rating_change": "N/A", "price_gap_pct": 0.0},
            "sentiment_breakdown": {"positive_pct": 0, "neutral_pct": 0, "negative_pct": 0, "top_complaints": [], "feature_requests": []},
            "pricing_analysis": {"your_price": 0.0, "competitor_avg": 0.0, "gap_pct": 0.0, "recommendation": "Upload pricing data to get recommendations."},
            "competitive_gaps": [],
            "root_cause": state.get("business_synthesis", "Analysis incomplete due to error."),
            "recommended_actions": [{"action": "Upload all data types for complete analysis", "priority": "High", "expected_impact": "Full insights"}],
            "confidence_score": 20.0,
            "data_completeness": "Low",
            "cost_usd": 0.0,
            "tokens_used": state.get("total_tokens_used", 0),
            "follow_up_suggestions": [],
            "duration_seconds": duration,
            "is_simple": state.get("is_simple", False),
        }

        publish_step(session_id, "report", "done", "Partial report ready")

        return {
            **state,
            "report": partial,
            "error": str(e),
            "completed_nodes": [*state.get("completed_nodes", []), "report_generator"],
        }
