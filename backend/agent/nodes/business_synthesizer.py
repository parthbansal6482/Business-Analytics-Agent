"""
Business Synthesizer: the most important node.
Connects all signal sources to produce the root cause and business narrative.
Applies KPI lens from user preferences.
"""

import logging
from agent.state import AgentState
from utils.llm import call_llm_with_retry, count_tokens
from utils.sse import publish_step

logger = logging.getLogger(__name__)

STYLE_INSTRUCTIONS = {
    "margin-focused":  "Focus on profitability, pricing power, and cost control. Highlight margin impact.",
    "growth-focused":  "Focus on conversion rate, customer acquisition, and revenue growth potential.",
    "gmv-focused":     "Focus on gross merchandise value (units × price), volume opportunities, and catalog expansion.",
}


def business_synthesizer(state: AgentState) -> AgentState:
    try:
        session_id = state["session_id"]
        prefs = state.get("user_preferences", {})
        analysis_style = prefs.get("analysis_style", "growth-focused")
        style_guide = STYLE_INSTRUCTIONS.get(analysis_style, STYLE_INSTRUCTIONS["growth-focused"])

        sentiment = state.get("sentiment_results", {})
        pricing   = state.get("pricing_results", {})
        competitor = state.get("competitor_results", {})
        catalog   = state.get("catalog_chunks", [])[:3]
        past      = state.get("past_analyses", [])

        prompt = f"""You are a senior e-commerce business analyst. Synthesize all data signals into a clear root cause.

USER CONTEXT:
- Analysis style: {analysis_style} — {style_guide}
- Preferred KPIs: {prefs.get('preferred_kpis', [])}
- Target marketplaces: {prefs.get('marketplaces', [])}
- Past analysis context: {past[:2]}

ORIGINAL QUERY: "{state['query']}"

DATA SIGNALS:

SENTIMENT ANALYSIS:
- Positive: {sentiment.get('positive_pct', 'N/A')}%, Neutral: {sentiment.get('neutral_pct', 'N/A')}%, Negative: {sentiment.get('negative_pct', 'N/A')}%
- Top complaints: {sentiment.get('top_complaints', [])}
- Feature requests: {sentiment.get('feature_requests', [])}
- Summary: {sentiment.get('sentiment_summary', '')}

PRICING ANALYSIS:
- Your price: {pricing.get('your_price', 'N/A')}, Competitor avg: {pricing.get('competitor_avg', 'N/A')}
- Price gap: {pricing.get('gap_pct', 'N/A')}%
- Elasticity: {pricing.get('price_elasticity', 'N/A')}
- SKU detail: {pricing.get('sku_analysis', '')}

COMPETITIVE GAPS:
- Feature gaps: {competitor.get('gaps', [])}
- Market positioning: {competitor.get('positioning', 'N/A')}
- Top threats: {competitor.get('top_threats', [])}

PRODUCT CATALOG SAMPLE:
{chr(10).join(catalog)}

TASK:
1. Identify the PRIMARY root cause connecting multiple signals (e.g., "pricing 16% above market + missing ANC feature + shipping delays are compounding into a 22% sales decline")
2. Write a 3-4 sentence business narrative that explains the "why" behind the numbers
3. Make specific, quantified claims using the data above

Write a 4-6 sentence root cause analysis that an e-commerce founder would find immediately actionable.
Use specific numbers. Connect at least 2 signals. Apply the {analysis_style} lens."""

        synthesis = call_llm_with_retry(prompt)
        tokens = count_tokens(prompt) + count_tokens(synthesis)

        publish_step(session_id, "synthesize", "done", "Business synthesis complete")

        return {
            **state,
            "business_synthesis": synthesis,
            "total_tokens_used": state.get("total_tokens_used", 0) + tokens,
            "completed_nodes": [*state.get("completed_nodes", []), "business_synthesizer"],
        }
    except Exception as e:
        logger.error(f"business_synthesizer error: {e}")
        return {
            **state,
            "business_synthesis": "Unable to synthesize business insights due to an error.",
            "error": str(e),
        }
