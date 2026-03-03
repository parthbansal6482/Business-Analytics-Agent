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


def _make_quick_report(state: AgentState, start_time: float) -> dict:
    """Quick mode: minimal Gemini calls, focused on top insights."""
    catalog_text = "\n".join(state.get("catalog_chunks", [])[:5])
    pricing_text = "\n".join(state.get("pricing_chunks", [])[:5])
    review_text  = "\n".join(state.get("review_chunks", [])[:5])

    prompt = f"""You are a senior e-commerce analyst. Give a quick business intelligence report.

Query: "{state['query']}"
User preferences: {state.get('user_preferences', {})}

Product data:
{catalog_text}

Pricing data:
{pricing_text}

Review samples:
{review_text}

Past context: {state.get('past_analyses', [])}

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

    prompt = f"""You are a senior e-commerce analyst. Generate a comprehensive intelligence report.

Query: "{state['query']}"
User preferences: {state.get('user_preferences', {})}

BUSINESS SYNTHESIS (root cause):
{synthesis}

SENTIMENT DATA: {json.dumps(sentiment)}
PRICING DATA: {json.dumps(pricing)}
COMPETITOR DATA: {json.dumps(competitor)}

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

        if mode == "deep":
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
        }

        publish_step(session_id, "report", "done", "Partial report ready")

        return {
            **state,
            "report": partial,
            "error": str(e),
            "completed_nodes": [*state.get("completed_nodes", []), "report_generator"],
        }
