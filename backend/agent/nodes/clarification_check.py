"""
Clarification Check: determines if the query is too vague to proceed.
"""

import logging
from utils.sse import publish_step
from utils.llm import call_llm_with_retry, count_tokens
from agent.state import AgentState

logger = logging.getLogger(__name__)

VAGUE_KEYWORDS = ["this", "it", "my product", "the product", "that item", "the sku"]


def clarification_check(state: AgentState) -> AgentState:
    try:
        query = state["query"].lower()
        session_id = state["session_id"]

        # Quick heuristic: if query is very short and uses generic pronouns
        is_likely_vague = (
            len(state["query"].split()) < 6
            and any(kw in query for kw in VAGUE_KEYWORDS)
        )

        if is_likely_vague:
            # Ask LLM to confirm vagueness
            prompt = f"""Is this e-commerce research query too vague to answer without knowing the specific product?

Query: "{state['query']}"

Reply with exactly one line:
VAGUE: yes OR no
If yes, add: QUESTION: [One crisp clarifying question to ask the user]"""

            response = call_llm_with_retry(prompt)
            lines = response.strip().split("\n")
            parsed = {}
            for line in lines:
                if ":" in line:
                    key, _, val = line.partition(":")
                    parsed[key.strip().upper()] = val.strip()

            if parsed.get("VAGUE", "no").lower() == "yes":
                question = parsed.get(
                    "QUESTION",
                    "Which product or SKU would you like me to analyze?"
                )
                publish_step(session_id, "clarify", "clarification", question)
                return {
                    **state,
                    "needs_clarification": True,
                    "clarification_question": question,
                    "completed_nodes": [*state.get("completed_nodes", []), "clarification_check"],
                }

        publish_step(session_id, "clarify", "done", "Query is clear")
        return {
            **state,
            "needs_clarification": False,
            "clarification_question": "",
            "completed_nodes": [*state.get("completed_nodes", []), "clarification_check"],
        }

    except Exception as e:
        logger.error(f"clarification_check error: {e}")
        # Non-fatal — proceed without clarification
        return {**state, "needs_clarification": False, "error": None}
