"""
Confidence scoring based on data completeness.
"""


def calculate_confidence(state: dict) -> float:
    score = 1.0
    if not state.get("catalog_chunks"):    score -= 0.20
    if not state.get("review_chunks"):     score -= 0.25
    if not state.get("pricing_chunks"):    score -= 0.20
    if not state.get("competitor_chunks"): score -= 0.15
    if state.get("error"):                 score -= 0.20
    return max(round(score, 2), 0.10)


def get_data_completeness(state: dict) -> str:
    sources = sum([
        bool(state.get("catalog_chunks")),
        bool(state.get("review_chunks")),
        bool(state.get("pricing_chunks")),
        bool(state.get("competitor_chunks")),
    ])
    if sources == 4: return "High"
    if sources >= 2: return "Moderate"
    return "Low"
