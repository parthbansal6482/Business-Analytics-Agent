"""
Business Synthesizer: Deep Mode multi-step reasoning.
Runs 3 sequential LLM passes: Signal Extraction → Critical Challenge → Final Synthesis.
All config comes from environment variables.
"""

import os
import logging
from agent.state import AgentState
from utils.llm import call_llm_with_retry, count_tokens
from utils.sse import publish_step

logger = logging.getLogger(__name__)

DEEP_TOP_K = int(os.getenv("DEEP_MODE_TOP_K", "30"))

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

        sentiment  = state.get("sentiment_results", {})
        pricing    = state.get("pricing_results", {})
        competitor = state.get("competitor_results", {})

        # Build shared data block from all retrieved chunks and analysis outputs
        data_block = f"""
PRODUCT CATALOG DATA:
{chr(10).join(f"- {c}" for c in state.get("catalog_chunks", [])[:DEEP_TOP_K])}

CUSTOMER REVIEW DATA:
{chr(10).join(f"- {c}" for c in state.get("review_chunks", [])[:DEEP_TOP_K])}

PRICING DATA:
{chr(10).join(f"- {c}" for c in state.get("pricing_chunks", [])[:DEEP_TOP_K])}

COMPETITOR DATA:
{chr(10).join(f"- {c}" for c in state.get("competitor_chunks", [])[:DEEP_TOP_K])}

SENTIMENT ANALYSIS RESULTS:
{sentiment}

PRICING ANALYSIS RESULTS:
{pricing}

COMPETITOR ANALYSIS RESULTS:
{competitor}
        """.strip()

        # ── PASS 1: Signal Extraction ─────────────────────────────────────────
        publish_step(session_id, "synthesize", "in_progress", "Extracting business signals…")
        pass1_prompt = f"""
You are a senior e-commerce business analyst with 15 years of experience in consumer electronics.
You specialize in finding hidden patterns in messy business data.

USER QUERY: "{state["query"]}"
USER CONTEXT: {past_context or "First session — no prior context."}

Here is the full business data:
{data_block}

Your task: SIGNAL EXTRACTION ONLY.

Extract every signal you can observe. Include:
- Revenue and sales signals (which products are up/down and by how much)
- Customer complaint signals (what specific issues appear repeatedly)
- Pricing signals (where is the user over or underpriced vs competitors)
- Feature gap signals (what do competitors have that this store doesn't)
- Inventory signals (overstock or stockout risks)
- Trend signals (anything changing over time)
- Weak signals (things that might matter but need more data to confirm)

Format as a numbered list. Be exhaustive. Do not draw conclusions yet.
Every signal must reference specific data points with numbers where available.

Good signal: "Battery complaints appear in 43 of 95 reviews (45%), specifically on SKU BT-115, concentrated in the last 60 days."
Bad signal: "Customers are unhappy." (too vague, no data reference)
""".strip()

        signals = call_llm_with_retry(pass1_prompt)
        tokens = count_tokens(pass1_prompt) + count_tokens(signals)

        # ── PASS 2: Critical Challenge ─────────────────────────────────────────
        publish_step(session_id, "synthesize", "in_progress", "Challenging the signals…")
        pass2_prompt = f"""
You are a skeptical business consultant reviewing a junior analyst's findings.

ORIGINAL USER QUERY: "{state["query"]}"

SIGNALS FOUND:
{signals}

Your task: CRITICAL ANALYSIS.

For each signal answer:
1. Is this signal STRONG (backed by solid data) or WEAK (could be noise)?
2. What alternative explanation could there be?
3. Are any signals contradicting each other? Which is more likely correct?
4. What important data is MISSING that would change the conclusion?
5. Which 3-5 signals most directly answer: "{state["query"]}"?

Be ruthless. Flag weak signals. The user needs accurate conclusions, not confident-sounding guesses.
""".strip()

        critique = call_llm_with_retry(pass2_prompt)
        tokens += count_tokens(pass2_prompt) + count_tokens(critique)

        # ── PASS 3: Final Synthesis ────────────────────────────────────────────
        publish_step(session_id, "synthesize", "in_progress", "Synthesizing root cause…")
        pass3_prompt = f"""
You are a Category P&L owner at a top-tier e-commerce company.
Root causes are almost never singular — they are combinations of 2-3 factors.
You never give vague conclusions. Every claim has a number behind it.

USER QUERY: "{state["query"]}"
ANALYSIS STYLE: {analysis_style} — {style_desc}

SIGNALS IDENTIFIED:
{signals}

CRITICAL ANALYSIS:
{critique}

Produce:

1. ROOT CAUSE (1-2 sentences)
   Must include specific numbers. Must combine at least 2 signals.

2. SUPPORTING EVIDENCE (3-5 bullet points)
   Strongest signals backing your conclusion. Each must have a number.

3. WHAT WAS RULED OUT (2-3 bullet points)
   Signals that looked important but were noise or secondary.

4. CONFIDENCE ASSESSMENT
   How confident are you? What would change this conclusion?

5. BUSINESS IMPACT ESTIMATE
   Approximate revenue/margin impact. Estimate if needed — say so clearly.

Apply the {analysis_style} lens throughout.
""".strip()

        synthesis = call_llm_with_retry(pass3_prompt)
        tokens += count_tokens(pass3_prompt) + count_tokens(synthesis)

        reasoning_trace = [
            f"PASS 1 — SIGNAL EXTRACTION:\n{signals}",
            f"PASS 2 — CRITICAL CHALLENGE:\n{critique}",
            f"PASS 3 — FINAL SYNTHESIS:\n{synthesis}",
        ]

        publish_step(session_id, "synthesize", "done", "Deep analysis complete (3-pass reasoning)")

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
