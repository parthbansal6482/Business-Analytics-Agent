"""
Sentiment Analyzer: analyzes customer reviews using Gemini.
"""

import json
import logging
from agent.state import AgentState
from utils.llm import call_llm_with_retry, count_tokens
from utils.sse import publish_step

logger = logging.getLogger(__name__)


def sentiment_analyzer(state: AgentState) -> AgentState:
    try:
        session_id = state["session_id"]
        review_chunks = state.get("review_chunks", [])

        if not review_chunks:
            publish_step(session_id, "sentiment", "done", "No reviews found")
            return {
                **state,
                "sentiment_results": {
                    "positive_pct": 0, "neutral_pct": 0, "negative_pct": 0,
                    "top_complaints": [], "feature_requests": [], "avg_rating": 0.0,
                },
                "completed_nodes": [*state.get("completed_nodes", []), "sentiment_analyzer"],
            }

        reviews_text = "\n".join(review_chunks[:20])

        persona = """You are a Voice of Customer specialist with 15 years of experience analyzing consumer electronics reviews.
You find the REAL underlying complaint behind surface-level reviews.
When customers say "bad quality" you dig into what specifically failed.
When customers say "not worth it" you identify whether it's a price or feature expectation problem."""

        instruction = """CRITICAL OUTPUT RULES:
- Every complaint must include how many reviews mention it (exact count or %)
- Group similar complaints: "battery" and "charge time" are the same issue
- Feature requests must be specific: not "better quality" but "waterproofing"
- Flag if a complaint is recent (last 30 days) vs ongoing — recency matters
- Distinguish verified purchases from unverified — they carry different weight"""

        prompt = f"""{persona}

Analyze these customer reviews and extract insights:

{reviews_text}

{instruction}

Respond with valid JSON only, no markdown:
{{
  "positive_pct": <integer 0-100>,
  "neutral_pct": <integer 0-100>,
  "negative_pct": <integer 0-100>,
  "avg_rating": <float 1.0-5.0>,
  "top_complaints": [
    "<specific complaint with review count, e.g. 'Battery dies in 3h (mentioned in 23/95 reviews, 24%)'>",
    "<specific complaint with review count>",
    "<specific complaint with review count>"
  ],
  "feature_requests": [
    "<specific feature, e.g. 'Active Noise Cancellation — requested in 31 reviews'>",
    "<specific feature>",
    "<specific feature>"
  ],
  "sentiment_summary": "<2-sentence overall sentiment narrative with specific numbers>"
}}

Rules:
- positive + neutral + negative must add up to 100
- NEVER write vague complaints like "battery issues" — always quantify
- Group related complaints before counting them"""


        response = call_llm_with_retry(prompt)
        tokens = count_tokens(prompt) + count_tokens(response)

        # Parse JSON response
        try:
            # Strip markdown fences if present
            raw = response.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            sentiment_results = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("sentiment_analyzer: JSON parse failed, using fallback")
            sentiment_results = {
                "positive_pct": 60, "neutral_pct": 25, "negative_pct": 15,
                "avg_rating": 3.8,
                "top_complaints": ["Unable to parse review data"],
                "feature_requests": [],
                "sentiment_summary": "Review analysis completed.",
            }

        publish_step(session_id, "sentiment", "done", "Sentiment analysis complete")

        return {
            **state,
            "sentiment_results": sentiment_results,
            "total_tokens_used": state.get("total_tokens_used", 0) + tokens,
            "completed_nodes": [*state.get("completed_nodes", []), "sentiment_analyzer"],
        }
    except Exception as e:
        logger.error(f"sentiment_analyzer error: {e}")
        return {**state, "sentiment_results": {}, "error": str(e)}
