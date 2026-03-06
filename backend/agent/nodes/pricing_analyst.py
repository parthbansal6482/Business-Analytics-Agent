"""
Pricing Analyst: analyzes pricing data and generates recommendations.
"""

import json
import logging
from agent.state import AgentState
from utils.llm import call_llm_with_retry, count_tokens
from utils.sse import publish_step

logger = logging.getLogger(__name__)


def pricing_analyst(state: AgentState) -> AgentState:
    try:
        session_id = state["session_id"]
        pricing_chunks  = state.get("pricing_chunks", [])
        catalog_chunks  = state.get("catalog_chunks", [])

        if not pricing_chunks and not catalog_chunks:
            publish_step(session_id, "pricing", "done", "No pricing data found")
            return {
                **state,
                "pricing_results": {
                    "your_price": 0.0, "competitor_avg": 0.0, "gap_pct": 0.0,
                    "recommendation": "No pricing data available.",
                },
                "completed_nodes": [*state.get("completed_nodes", []), "pricing_analyst"],
            }

        catalog_text  = "\n".join(state.get("catalog_chunks",    [])[:15])
        pricing_text  = "\n".join(state.get("pricing_chunks",    [])[:15])
        competitor_text = "\n".join(state.get("competitor_chunks",[])[:15])

        persona = """You are a pricing strategist who previously worked at a top consulting firm advising consumer electronics brands.
You understand that price perception matters as much as actual price.
A product 16% above market needs to justify that premium with visible, tangible features or it will lose to competitors."""

        instruction = """CRITICAL OUTPUT RULES:
- Calculate exact price gap % for every SKU where competitor data exists
- Flag products MORE than 10% above market average (danger zone)
- Flag products MORE than 10% below market average (margin leak)
- Correlate price changes with sales volume changes where data exists
- Give a specific price recommendation with the target number, not just "reduce price" """

        prompt = f"""{persona}

Analyze this pricing data and provide a pricing intelligence report:

PRODUCT CATALOG:
{catalog_text}

PRICING DATA:
{pricing_text}

COMPETITOR PRICING:
{competitor_text}

{instruction}

Respond with valid JSON only, no markdown:
{{
  "your_price": <float, average or most common user product price>,
  "competitor_avg": <float, average competitor price>,
  "gap_pct": <float, (your_price - competitor_avg) / competitor_avg * 100>,
  "price_elasticity": "<high/medium/low> — observed sensitivity to price changes",
  "sku_analysis": "<table or list: SKU | Your Price | Comp Avg | Gap% | Status>",
  "pricing_opportunities": ["<specific opportunity with numbers>", "<opportunity>"],
  "recommendation": "<specific recommendation with exact target price and expected impact>"
}}"""

        response = call_llm_with_retry(prompt)
        tokens = count_tokens(prompt) + count_tokens(response)

        try:
            raw = response.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            pricing_results = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("pricing_analyst: JSON parse failed")
            pricing_results = {
                "your_price": 0.0, "competitor_avg": 0.0, "gap_pct": 0.0,
                "recommendation": "Pricing data could not be parsed."
            }

        publish_step(session_id, "pricing", "done", "Pricing analysis complete")

        return {
            **state,
            "pricing_results": pricing_results,
            "total_tokens_used": state.get("total_tokens_used", 0) + tokens,
            "completed_nodes": [*state.get("completed_nodes", []), "pricing_analyst"],
        }
    except Exception as e:
        logger.error(f"pricing_analyst error: {e}")
        return {**state, "pricing_results": {}, "error": str(e)}
