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
    reasoning_trace: list[str] = []


def _make_simple_report(state: AgentState) -> tuple[str, int]:
    """Extremely fast path for simple data lookups."""
    catalog_text  = "\n".join(state.get("catalog_chunks", [])[:5])
    pricing_text  = "\n".join(state.get("pricing_chunks", [])[:3])
    review_text   = "\n".join(state.get("review_chunks",  [])[:3])
    order_text    = "\n".join(state.get("order_chunks",   [])[:3])
    customer_text = "\n".join(state.get("customer_chunks",[])[:3])

    total_products  = state.get('total_products_synced')
    total_orders    = state.get('total_orders_synced')
    total_customers = state.get('total_customers_synced')
    db_note = ""
    if any(v not in (None, 'Unknown', 0) for v in [total_products, total_orders, total_customers]):
        db_note = f"""
Database Record Counts (use ONLY when query explicitly asks for totals):
- Total Products: {total_products}
- Total Orders: {total_orders}
- Total Customers: {total_customers}
"""

    prompt = f"""You are a helpful e-commerce assistant. Answer the user's question directly.

Query: "{state['query']}"
{db_note}
Data Context (use THIS to answer product/sales/complaint questions):
Product Catalog (includes sales_volume per product): {catalog_text}
Pricing: {pricing_text}
Reviews: {review_text}
Orders: {order_text}
Customers: {customer_text}

IMPORTANT RULES:
- For "best-selling SKU" or "top product" questions: rank by sales_volume in the catalog data. If all tied, pick the top 3 and name them anyway. Fall back to rating if needed. NEVER say 'not determinable'.
- Do NOT say "no orders" if catalog data has sales_volume values — those ARE the sales signal.
- Only use Database Record Counts for explicit count/total questions.
- NEVER output the past context verbatim. NEVER say 'Prior context considered' in your answer.

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
    """Quick mode: minimal LLM calls, focused on top insights."""
    catalog_text  = "\n".join(state.get("catalog_chunks", [])[:10])
    pricing_text  = "\n".join(state.get("pricing_chunks", [])[:5])
    review_text   = "\n".join(state.get("review_chunks",  [])[:5])
    order_text    = "\n".join(state.get("order_chunks",   [])[:5])
    customer_text = "\n".join(state.get("customer_chunks",[])[:5])

    total_products  = state.get('total_products_synced')
    total_orders    = state.get('total_orders_synced')
    total_customers = state.get('total_customers_synced')
    db_note = ""
    if any(v not in (None, 'Unknown', 0) for v in [total_products, total_orders, total_customers]):
        db_note = f"""
Database Record Counts (use ONLY when query asks for explicit totals):
- Total Products: {total_products}
- Total Orders: {total_orders}
- Total Customers: {total_customers}
"""

    prompt = f"""You are a senior e-commerce analyst. Give a quick business intelligence report.

Query: "{state['query']}"
User preferences: {state.get('user_preferences', {})}
{db_note}
Data Context (use THIS to answer product/sales/pricing/review questions):
Product Catalog (includes sales_volume per product — higher = better seller):
{catalog_text}

Pricing data:
{pricing_text}

Review samples:
{review_text}

Order history:
{order_text}

Customer activity:
{customer_text}

CRITICAL RULES:
- For best-selling SKU / top product questions: rank by sales_volume from the catalog data. If all values are tied, still pick and name the top SKUs — do NOT say 'not determinable'. Fall back to rating or inventory.
- For explicit count questions ("how many orders"): use Database Record Counts only.
- Never assume data is missing just because DB counts are Unknown — the catalog+review data above is your primary source.

Respond with valid JSON exactly matching this schema (no markdown fences):
{{
  "executive_summary": "<3-4 sentence business summary that DIRECTLY answers the query with specific data>",
  "key_metrics": {{
    "revenue_impact": "<e.g. Best seller: SKU X with 11 units sold>",
    "rating_change": "<e.g. +0.3 Stars or N/A>",
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

    evidence_rules = """
EVIDENCE RULES — STRICTLY ENFORCED:
Every claim must follow this format: Claim [Evidence: specific data point that proves this]

BANNED PHRASES — never use these:
  ✗ "customers are unhappy"  ✗ "sales are declining"  ✗ "pricing is an issue"  ✗ "competitors are stronger"

REQUIRED FORMAT instead:
  ✓ "Battery life is the top complaint (43/95 reviews, 45%) [Evidence: reviews, SKU BT-115]"
  ✓ "Price is 16.7% above market avg [Evidence: BT-115 at ₹3,499 vs competitor avg ₹2,999]"
  ✓ "Competitor SoundMax Pro has ANC which 31 customers requested [Evidence: reviews feature_requests]"

CONFIDENCE SCORING RULES:
  - Above 0.85 only if all 4 data sources had substantial data
  - 0.70-0.85 if 3 sources had data
  - Below 0.70 if only 1-2 sources had data
  - NEVER give 1.0 or 100% — business data always has uncertainty
"""

    db_metrics_note = ""
    total_products = state.get('total_products_synced')
    total_orders   = state.get('total_orders_synced')
    total_customers = state.get('total_customers_synced')
    if any(v not in (None, 'Unknown', 0) for v in [total_products, total_orders, total_customers]):
        db_metrics_note = f"""
Database Record Counts (use ONLY when the query explicitly asks for totals/counts):
- Total Products in DB: {total_products}
- Total Orders in DB: {total_orders}
- Total Customers in DB: {total_customers}
"""

    prompt = f"""You are a senior e-commerce analyst. Generate a comprehensive intelligence report.

Query: "{state['query']}"
User preferences: {state.get('user_preferences', {})}

⚠️ PRIMARY SOURCE — TRUST THIS ABOVE ALL ELSE:
The following is the result of a rigorous 3-pass deep analysis. Your executive_summary and root_cause MUST
align with this synthesis. Do NOT contradict it or invent alternative conclusions.

BUSINESS SYNTHESIS:
{synthesis}
{db_metrics_note}
SUPPLEMENTARY ANALYSIS DATA:
SENTIMENT: {json.dumps(sentiment)}
PRICING: {json.dumps(pricing)}
COMPETITOR: {json.dumps(competitor)}
ORDER SIGNALS: {order_text}
CUSTOMER SIGNALS: {customer_text}

{evidence_rules}

Respond with valid JSON exactly matching this schema (no markdown fences):
{{
  "executive_summary": "<4-5 sentence business overview that DIRECTLY answers the query — cite the synthesis>",
  "key_metrics": {{
    "revenue_impact": "<e.g. Best seller: 11 units, $979 estimated revenue>",
    "rating_change": "<e.g. +0.3 Stars>",
    "price_gap_pct": <float from pricing data, 0.0 if unknown>
  }},
  "sentiment_breakdown": {{
    "positive_pct": <from sentiment data>, "neutral_pct": <int>, "negative_pct": <int>,
    "top_complaints": <from sentiment data>,
    "feature_requests": <from sentiment data>
  }},
  "pricing_analysis": {{
    "your_price": <from pricing data, 0.0 if unknown>, "competitor_avg": <from pricing data, 0.0 if unknown>,
    "gap_pct": <from pricing data, 0.0 if unknown>,
    "recommendation": "<specific recommendation with numbers>"
  }},
  "competitive_gaps": <from competitor data gaps list>,
  "root_cause": "<copy the ROOT CAUSE from the business synthesis above — do not rephrase away from it>",
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

        # Preserve reasoning_trace from business_synthesizer (Deep Mode only)
        if "reasoning_trace" not in report_dict or not report_dict["reasoning_trace"]:
            report_dict["reasoning_trace"] = state.get("reasoning_trace", [])

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
            "reasoning_trace": report_out["reasoning_trace"],
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
