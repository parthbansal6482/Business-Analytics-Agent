"""
Intent Classifier: determines query intent and validates/overrides mode.
"""

import logging
from utils.sse import publish_step
from utils.llm import call_llm_with_retry, count_tokens
from agent.state import AgentState

logger = logging.getLogger(__name__)

def intent_classifier(state: AgentState) -> AgentState:
    try:
        query = state["query"]
        user_prefs = state.get("user_preferences", {})
        mode = state.get("mode", "quick")
        history = state.get("conversation_history", [])
        is_followup = len(history) > 0
        updated_query = query

        # ── Follow-up detection (moved to top for better classification) ──
        if is_followup:
            last_assistant = next(
                (m["content"] for m in reversed(history) if m["role"] == "assistant"),
                ""
            )
            # Truncate to avoid blowing up context
            context = f"\n\nContext from previous analysis:\n{last_assistant[:1500]}"
            updated_query = query + context

        prompt = f"""You are an e-commerce intelligence system. Classify this business query.

Query: "{updated_query}"
Current mode: {mode}

Respond in this exact format:
MODE: quick OR deep
INTENT: [2-3 word intent label, e.g. "sentiment analysis", "pricing review", "competitor gaps"]
DATA_NEEDED: [comma-separated: catalog, reviews, pricing, competitors]
COMPLEXITY: [simple/medium/complex]

Rules:
- Use "deep" if query mentions multiple products, trends over time, root cause, or "comprehensive"
- Use "quick" for single metric questions or sentiment summaries"""

        response = call_llm_with_retry(prompt)
        lines = response.strip().split("\n")
        parsed = {}
        for line in lines:
            if ":" in line:
                key, _, val = line.partition(":")
                parsed[key.strip().upper()] = val.strip()

        # Override mode only if LLM says deep and user didn't force quick
        if parsed.get("MODE", "quick").lower() == "deep":
            mode = "deep"

        # Determine if it's a simple query based on complexity
        is_simple = parsed.get("COMPLEXITY", "").lower() == "simple"

        tokens = count_tokens(prompt) + count_tokens(response)

        publish_step(state["session_id"], "intent", "done", "Intent understood")

        return {
            **state,
            "query": updated_query,
            "mode": mode,
            "is_simple": is_simple,
            "is_followup": is_followup,
            "total_tokens_used": state.get("total_tokens_used", 0) + tokens,
            "completed_nodes": [*state.get("completed_nodes", []), "intent_classifier"],
        }
    except Exception as e:
        logger.error(f"intent_classifier error: {e}")
        return {**state, "error": str(e), "is_simple": False, "is_followup": False}
