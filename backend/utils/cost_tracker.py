"""
Token counting and cost tracking.
Gemini 2.0 Flash free tier = $0.00 cost.
Tokens are tracked for transparency / judge scoring.
"""

import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from utils.llm import count_tokens

logger = logging.getLogger(__name__)


def get_session_cost(total_tokens: int) -> float:
    """Gemini 2.0 Flash free tier → always $0.00."""
    return 0.0


def estimate_tokens(text: str) -> int:
    """DEPRECATED: Use utils.llm.count_tokens instead."""
    return count_tokens(text)


async def log_tokens(
    db: AsyncSession,
    session_id: str,
    node_name: str,
    input_text: str,
    output_text: str,
) -> int:
    """Log token usage to DB and return total for this call."""
    from db.models import TokenLog
    input_tokens = estimate_tokens(input_text)
    output_tokens = estimate_tokens(output_text)
    total = input_tokens + output_tokens

    try:
        log = TokenLog(
            session_id=session_id,
            node_name=node_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        db.add(log)
        await db.flush()
    except Exception as e:
        logger.warning(f"Failed to log tokens: {e}")

    return total
