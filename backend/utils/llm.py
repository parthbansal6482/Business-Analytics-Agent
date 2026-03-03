"""
Gemini 2.0 Flash LLM setup with exponential-backoff retry.
All agent nodes must use call_llm_with_retry — never llm.invoke() directly.
"""

import os
import time
import logging
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY", ""),
    temperature=0.2,
    max_tokens=8192,
)


def call_llm_with_retry(prompt: str, retries: int = 4) -> str:
    """Call Gemini with exponential backoff on rate-limit errors."""
    for attempt in range(retries):
        try:
            response = llm.invoke(prompt)
            return response.content
        except Exception as e:
            err = str(e)
            if "429" in err or "quota" in err.lower() or "rate" in err.lower():
                wait = 2 ** attempt
                logger.warning(f"Rate limit hit. Retrying in {wait}s (attempt {attempt + 1}/{retries})")
                time.sleep(wait)
            elif "503" in err or "unavailable" in err.lower():
                wait = 2 ** attempt
                logger.warning(f"Service unavailable. Retrying in {wait}s")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("LLM call failed after max retries")


def count_tokens(text: str) -> int:
    """Rough token estimate (4 chars ≈ 1 token)."""
    return max(1, len(text) // 4)
