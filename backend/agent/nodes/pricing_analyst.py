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

        pricing_text = "\n".join(pricing_chunks[:15])
        catalog_text = "\n".join(catalog_chunks[:5])

        prompt = f"""You are a pricing strategist for an e-commerce brand.

Product data:
{catalog_text}

Pricing data (your prices vs competitors):
{pricing_text}

Query context: {state['query']}

Respond with valid JSON only, no markdown:
{{
  "your_price": <your average or flagship product price as a number>,
  "competitor_avg": <competitor average price as a number>,
  "gap_pct": <price gap percentage, positive = you are more expensive>,
  "price_elasticity": "<elastic/inelastic/unknown>",
  "recommendation": "<1-2 sentence actionable pricing recommendation with specific numbers>",
  "sku_analysis": "<which specific SKU(s) are most affected and why>"
}}

Be specific with numbers. If data shows BT-115 at ₹3499 vs competitors at ₹2999, say so."""

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
