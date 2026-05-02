"""
Combined Analyzer: merges sentiment, pricing, and competitor analysis into a
single LLM call for Deep Mode. This cuts 3 separate LLM calls down to 1,
keeping Deep Mode within Groq's free tier TPM limits.
"""

import os
import json
import logging
from agent.state import AgentState
from utils.llm import call_llm_with_retry, count_tokens
from utils.sse import publish_step

logger = logging.getLogger(__name__)

MAX_CHUNK_CHARS = int(os.getenv("MAX_CHUNK_CHARS", "200"))


def _trim(chunks: list[str], n: int = 10) -> str:
    return "\n".join(f"- {c[:MAX_CHUNK_CHARS]}" for c in chunks[:n])


def combined_analyzer(state: AgentState) -> AgentState:
    """
    Single LLM call that produces sentiment, pricing, and competitor analysis.
    Replaces the 3 separate nodes (sentiment_analyzer, pricing_analyst, competitor_analyzer).
    """
    try:
        session_id = state["session_id"]
        publish_step(session_id, "analyze", "in_progress", "Running combined analysis…")

        review_text     = _trim(state.get("review_chunks", []),    n=15)
        pricing_text    = _trim(state.get("pricing_chunks", []),   n=10)
        competitor_text = _trim(state.get("competitor_chunks", []), n=10)
        catalog_text    = _trim(state.get("catalog_chunks", []),   n=5)

        global_stats = state.get("global_stats", {})
        stats_text = json.dumps(global_stats, indent=2)

        prompt = f"""You are an expert e-commerce analyst. Analyze the data below and return a single JSON object.

QUERY: "{state['query']}"

GLOBAL DATA STATISTICS (Across ALL your data):
{stats_text}

REVIEW SAMPLES (Specific matches):
{review_text or "(no reviews available)"}

PRICING DATA (Specific matches):
{pricing_text or "(no pricing data available)"}

COMPETITOR DATA (Specific matches):
{competitor_text or "(no competitor data available)"}

CATALOG SAMPLE (Specific matches):
{catalog_text or "(no catalog available)"}

Return ONLY valid JSON with this exact structure (no markdown fences):
{{
  "sentiment": {{
    "positive_pct": <int 0-100>,
    "neutral_pct": <int 0-100>,
    "negative_pct": <int 0-100>,
    "avg_rating": <float>,
    "top_complaints": ["<complaint with count>", "<complaint with count>"],
    "feature_requests": ["<request>", "<request>"],
    "review_count": <int>
  }},
  "pricing": {{
    "your_price": <float or 0>,
    "competitor_avg": <float or 0>,
    "gap_pct": <float — positive means you are above market>,
    "danger_skus": ["<SKU:gap%>"],
    "margin_leak_skus": ["<SKU:gap%>"],
    "recommendation": "<1 sentence with specific numbers>"
  }},
  "competitors": {{
    "top_competitor": "<name>",
    "critical_gaps": ["<feature your products lack that competitors have>"],
    "your_strengths": ["<feature advantage you have>"],
    "threat_level": "<Low|Medium|High>"
  }}
}}"""

        raw = call_llm_with_retry(prompt)
        tokens = count_tokens(prompt) + count_tokens(raw)

        try:
            # Strip any markdown fences if the LLM added them anyway
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("combined_analyzer: JSON parse failed, using empty results")
            data = {}

        sentiment_results  = data.get("sentiment",    {})
        pricing_results    = data.get("pricing",      {})
        competitor_results = data.get("competitors",  {})

        publish_step(session_id, "analyze", "done",
                     f"Analysis complete — sentiment: {sentiment_results.get('positive_pct', 0)}% positive, "
                     f"price gap: {pricing_results.get('gap_pct', 0):.1f}%, "
                     f"top competitor: {competitor_results.get('top_competitor', 'N/A')}")

        return {
            **state,
            "sentiment_results":  sentiment_results,
            "pricing_results":    pricing_results,
            "competitor_results": competitor_results,
            "completed_nodes": [*state.get("completed_nodes", []), "combined_analyzer"],
        }

    except Exception as e:
        logger.error(f"combined_analyzer error: {e}")
        return {
            **state,
            "sentiment_results":  {},
            "pricing_results":    {},
            "competitor_results": {},
            "error": str(e),
        }
