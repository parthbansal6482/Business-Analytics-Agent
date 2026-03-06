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

        catalog_text    = "\n".join(state.get("catalog_chunks",    [])[:15])
        competitor_text = "\n".join(state.get("competitor_chunks", [])[:15])
        pricing_text    = "\n".join(state.get("pricing_chunks",    [])[:5])

        persona = """You are a competitive intelligence analyst specializing in consumer electronics.
You know that the most dangerous competitor gaps are the ones customers can see immediately on a product listing — battery hours, ANC yes/no, connectivity version.
You separate features that drive purchase decisions from features that just sound good."""

        instruction = """CRITICAL OUTPUT RULES:
- Build an explicit feature-by-feature comparison
- Mark each gap as CRITICAL (purchase decision driver) or MINOR (nice to have)
- Identify the single most dangerous competitor (best combo of price + features + rating)
- Find gaps where you are AHEAD of competitors — these are your strengths
- Estimate how much each critical gap is costing in lost sales if data allows"""

        prompt = f"""{persona}

Analyze the competitive landscape for this e-commerce business:

OUR PRODUCTS:
{catalog_text}

COMPETITOR PRODUCTS:
{competitor_text}

OUR PRICING (sample):
{pricing_text}

{instruction}

Respond with valid JSON only, no markdown:
{{
  "gaps": [
    "<CRITICAL gap: missing feature competitors have, e.g. 'CRITICAL — ANC missing; SoundMax Pro has it, 31 customers requested it'>",
    "<CRITICAL gap>",
    "<MINOR gap>",
    "<MINOR gap>"
  ],
  "strengths": ["<area where you are ahead with evidence>", "<strength>"],
  "positioning": "<your current market position — premium/value/mid-range and why>",
  "top_threats": ["<most dangerous competitor with reason>", "<threat>"],
  "most_dangerous_competitor": "<name + why they're most dangerous>",
  "competitive_summary": "<2-3 sentence competitive narrative with specific gaps and strengths>"
}}"""


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
