"""
Competitor Analyzer: identifies feature gaps and competitive positioning.
"""

import json
import logging
from agent.state import AgentState
from utils.llm import call_llm_with_retry, count_tokens
from utils.sse import publish_step

logger = logging.getLogger(__name__)


def competitor_analyzer(state: AgentState) -> AgentState:
    try:
        session_id = state["session_id"]
        competitor_chunks = state.get("competitor_chunks", [])

        if not competitor_chunks:
            publish_step(session_id, "competitor", "done", "No competitor data")
            return {
                **state,
                "competitor_results": {"gaps": [], "positioning": "Unknown", "top_threats": []},
                "completed_nodes": [*state.get("completed_nodes", []), "competitor_analyzer"],
            }

        competitor_text = "\n".join(competitor_chunks[:15])
        catalog_text = "\n".join(state.get("catalog_chunks", [])[:3])

        prompt = f"""You are a competitive intelligence analyst for an e-commerce brand.

Your products:
{catalog_text}

Competitor data:
{competitor_text}

Query: {state['query']}

Respond with valid JSON only, no markdown:
{{
  "gaps": [
    "<Feature competitors have that you lack — be specific, e.g. 'ANC noise cancellation (SoundMax Pro, AudioPlus X1) — you: Missing'>",
    "<another gap>",
    "<another gap>",
    "<another gap>"
  ],
  "positioning": "<premium/budget/value/undifferentiated>",
  "top_threats": [
    "<Competitor name>: <why they are a threat in one sentence>",
    "<Competitor name>: <why they are a threat in one sentence>"
  ],
  "market_summary": "<2-sentence market position analysis>"
}}

Each gap should be actionable and include which competitor(s) have the feature."""

        response = call_llm_with_retry(prompt)
        tokens = count_tokens(prompt) + count_tokens(response)

        try:
            raw = response.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            competitor_results = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("competitor_analyzer: JSON parse failed")
            competitor_results = {"gaps": [], "positioning": "Unknown", "top_threats": []}

        publish_step(session_id, "competitor", "done", "Competitor analysis complete")

        return {
            **state,
            "competitor_results": competitor_results,
            "total_tokens_used": state.get("total_tokens_used", 0) + tokens,
            "completed_nodes": [*state.get("completed_nodes", []), "competitor_analyzer"],
        }
    except Exception as e:
        logger.error(f"competitor_analyzer error: {e}")
        return {**state, "competitor_results": {}, "error": str(e)}
