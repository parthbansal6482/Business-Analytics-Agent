"""
Business Synthesizer: Deep Mode multi-step reasoning.
Runs 3 sequential LLM passes: Signal Extraction → Critical Challenge → Final Synthesis.
All config comes from environment variables.
"""

import os
import time
import logging
from agent.state import AgentState
from utils.llm import call_llm_with_retry, count_tokens
from utils.sse import publish_step

logger = logging.getLogger(__name__)

DEEP_TOP_K = int(os.getenv("DEEP_MODE_TOP_K", "30"))
MAX_CHUNK_CHARS = int(os.getenv("MAX_CHUNK_CHARS", "200"))
MAX_DATA_BLOCK_CHARS = int(os.getenv("MAX_DATA_BLOCK_CHARS", "6000"))


def _truncate_chunks(chunks: list[str], max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """Truncate each chunk to a max length to stay within token budgets."""
    return [c[:max_chars] + ("…" if len(c) > max_chars else "") for c in chunks]


def _build_data_block(state: AgentState, top_k: int) -> str:
    """Build the context data block with a hard character cap."""
    sections = [
        ("PRODUCT CATALOG DATA", state.get("catalog_chunks", [])[:top_k]),
        ("CUSTOMER REVIEW DATA", state.get("review_chunks", [])[:top_k]),
        ("PRICING DATA",         state.get("pricing_chunks", [])[:top_k]),
        ("COMPETITOR DATA",      state.get("competitor_chunks", [])[:top_k]),
    ]
    parts = []
    total_chars = 0
    for title, chunks in sections:
        if not chunks:
            parts.append(f"{title}:\n(no data)")
            continue
        truncated = _truncate_chunks(chunks)
        block = f"{title}:\n" + "\n".join(f"- {c}" for c in truncated)
        if total_chars + len(block) > MAX_DATA_BLOCK_CHARS:
            # Add what fits, then stop
            remaining = MAX_DATA_BLOCK_CHARS - total_chars
            block = block[:remaining] + "\n[…truncated to stay within token budget]"
            parts.append(block)
            break
        parts.append(block)
        total_chars += len(block)

    # Always append the computed analysis results (they are small JSON dicts)
    parts.append(f"SENTIMENT ANALYSIS RESULTS:\n{state.get('sentiment_results', {})}")
    parts.append(f"PRICING ANALYSIS RESULTS:\n{state.get('pricing_results', {})}")
    parts.append(f"COMPETITOR ANALYSIS RESULTS:\n{state.get('competitor_results', {})}")
    parts.append(f"GLOBAL DATA AGGREGATES (Full dataset totals/averages):\n{state.get('global_stats', {})}")
    return "\n\n".join(parts)


STYLE_INSTRUCTIONS = {
    "margin-focused": "emphasize pricing power, cost control, and discount impact",
    "growth-focused": "emphasize conversion, traffic, category expansion",
    "gmv-focused":    "emphasize volume × price optimization",
}


def business_synthesizer(state: AgentState) -> AgentState:
    try:
        session_id     = state["session_id"]
        prefs          = state.get("user_preferences", {})
        analysis_style = prefs.get("analysis_style", "growth-focused")
        style_desc     = STYLE_INSTRUCTIONS.get(analysis_style, STYLE_INSTRUCTIONS["growth-focused"])
        past_context   = "\n".join(state.get("past_analyses", []))

        # Build context data block with token budget to avoid Groq TPM limits
        data_block = _build_data_block(state, DEEP_TOP_K)

        # ── PASS 1: Signal Extraction + Critical Analysis (combined) ──────────
        publish_step(session_id, "synthesize", "in_progress", "Extracting and evaluating business signals…")
        pass1_prompt = f"""You are a senior e-commerce business analyst and skeptical consultant.

USER QUERY: "{state["query"]}"
ANALYSIS STYLE: {analysis_style} — {style_desc}
PRIOR CONTEXT: {past_context or "First session."}

BUSINESS DATA:
{data_block}

TASK — Do both steps in sequence:

STEP A — SIGNAL EXTRACTION:
List every observable signal with specific numbers. Cover: sales/revenue signals,
customer complaints, pricing gaps vs competitors, feature gaps, inventory risks.
Mark each as STRONG or WEAK with a short reason.

STEP B — CRITICAL FILTER:
From Step A, identify the 3-5 signals that most directly answer: "{state["query"]}"
Rule out signals that are noise or missing data. Note any contradictions.

Format:
SIGNALS:
1. [STRONG/WEAK] <signal with numbers>
...

KEY SIGNALS FOR QUERY:
- <most relevant signal>
...

WHAT WAS RULED OUT:
- <noise signal and why>
...
""".strip()

        signals_and_critique = call_llm_with_retry(pass1_prompt)
        tokens = count_tokens(pass1_prompt) + count_tokens(signals_and_critique)

        # Brief pause between passes
        time.sleep(3)

        # ── PASS 2: Final Synthesis ────────────────────────────────────────────
        publish_step(session_id, "synthesize", "in_progress", "Synthesizing root cause…")
        pass2_prompt = f"""You are a Category P&L owner. Every claim needs a number. Root causes combine 2-3 factors.

USER QUERY: "{state["query"]}"

ANALYSIS:
{signals_and_critique}

Produce:
1. ROOT CAUSE (1-2 sentences with specific numbers, combining at least 2 signals)
2. SUPPORTING EVIDENCE (3-5 bullet points, each with a number)
3. WHAT WAS RULED OUT (2-3 bullets)
4. CONFIDENCE ASSESSMENT (0-100% with reasoning)
5. BUSINESS IMPACT ESTIMATE (revenue/margin in $ or %, state if estimated)
""".strip()

        synthesis = call_llm_with_retry(pass2_prompt)
        tokens += count_tokens(pass2_prompt) + count_tokens(synthesis)

        reasoning_trace = [
            f"PASS 1 — SIGNAL EXTRACTION & CRITICAL ANALYSIS:\n{signals_and_critique}",
            f"PASS 2 — FINAL SYNTHESIS:\n{synthesis}",
        ]

        publish_step(session_id, "synthesize", "done", "Deep analysis complete (2-pass reasoning)")

        return {
            **state,
            "business_synthesis": synthesis,
            "reasoning_trace":    reasoning_trace,
            "total_tokens_used":  state.get("total_tokens_used", 0) + tokens,
            "completed_nodes":    [*state.get("completed_nodes", []), "business_synthesizer"],
        }

    except Exception as e:
        logger.error(f"business_synthesizer error: {e}")
        return {
            **state,
            "business_synthesis": "Unable to synthesize business insights due to an error.",
            "reasoning_trace":    [],
            "error":              str(e),
        }
