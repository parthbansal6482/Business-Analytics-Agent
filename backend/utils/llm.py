"""
Gemini 2.0 Flash LLM setup with exponential-backoff retry.
All agent nodes must use call_llm_with_retry — never llm.invoke() directly.
"""

import os
import time
import logging
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

_llm = None

def get_llm():
    """Lazy initialization of the LLM to ensure environment variables are loaded."""
    global _llm
    if _llm is None:
        api_key = os.getenv("GOOGLE_API_KEY", "")
        if not api_key:
            # Try to force reload one last time if missing
            from dotenv import load_dotenv
            import pathlib
            load_dotenv(dotenv_path=pathlib.Path(__file__).parent.parent / ".env", override=True)
            api_key = os.getenv("GOOGLE_API_KEY", "")

        if not api_key:
            logger.error("❌ GOOGLE_API_KEY is completely missing or empty!")
            raise RuntimeError("GOOGLE_API_KEY not found in environment")
        
        logger.info(f"✅ Initializing Gemini LLM (key starts with {api_key[:6]}...)")
        _llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=api_key,
            temperature=0.2,
            max_tokens=8192,
            max_retries=0, # Disable internal retries so we can control wait times
        )
    return _llm


import random

def call_llm_with_retry(prompt: str, retries: int = 6) -> str:
    """Call Gemini with conservative exponential backoff for free-tier quotas."""
    model = get_llm()
    for attempt in range(retries):
        try:
            response = model.invoke(prompt)
            return response.content
        except Exception as e:
            err = str(e)
            
            # Fail fast if daily quota is exhausted
            if "GenerateRequestsPerDay" in err or "quota for this API has been exhausted" in err.lower():
                logger.error("Daily LLM quota exhausted. Failing immediately.")
                raise RuntimeError("Gemini Free Tier daily quota exhausted. Please try again tomorrow or upgrade your API key.")
                
            # If 429 (Rate Limit) or 503 (Unavailable)
            if any(code in err for code in ["429", "503"]) or any(kw in err.lower() for kw in ["quota", "rate", "unavailable", "exhausted"]):
                # Increase wait more aggressively for free tier (which has 15 RPM limit)
                base_wait = 5 * (2 ** attempt)
                wait = base_wait + random.uniform(0, base_wait * 0.5)
                # Cap the maximum wait time to avoid hanging the UI endlessly (e.g., max 30s)
                wait = min(wait, 30.0)
                
                logger.warning(f"LLM limit reached ({err[:50]}...). Retrying in {wait:.1f}s (attempt {attempt + 1}/{retries})")
                time.sleep(wait)
            else:
                logger.error(f"Non-retryable LLM error: {err}")
                raise
    raise RuntimeError("LLM call failed after max retries")


def count_tokens(text: str) -> int:
    """Rough token estimate (4 chars ≈ 1 token)."""
    return max(1, len(text) // 4)
