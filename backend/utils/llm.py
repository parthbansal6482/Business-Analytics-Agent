import os
import time
import random
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq

logger = logging.getLogger(__name__)

_llm = None

def get_llm():
    """Lazy initialization of the LLM to ensure environment variables are loaded."""
    global _llm
    if _llm is None:
        provider = os.getenv("LLM_PROVIDER", "gemini").lower()

        # Ensure environment is loaded
        from dotenv import load_dotenv
        import pathlib
        load_dotenv(dotenv_path=pathlib.Path(__file__).parent.parent / ".env", override=True)

        temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
        max_tokens  = int(os.getenv("LLM_MAX_TOKENS", "4096"))

        if provider == "openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY", "")
            if not api_key:
                logger.error("❌ OPENROUTER_API_KEY is missing!")
                raise RuntimeError("OPENROUTER_API_KEY not found in environment")

            model_name = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
            logger.info(f"✅ Initializing OpenRouter LLM (model: {model_name})")
            _llm = ChatOpenAI(
                model=model_name,
                openai_api_key=api_key,
                openai_api_base="https://openrouter.ai/api/v1",
                temperature=temperature,
                max_tokens=max_tokens,
                default_headers={
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": "Business Analytics Agent",
                }
            )
        elif provider == "groq":
            api_key = os.getenv("GROQ_API_KEY", "")
            if not api_key:
                logger.error("❌ GROQ_API_KEY is missing!")
                raise RuntimeError("GROQ_API_KEY not found in environment")

            model_name = os.getenv("LLM_MODEL") or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
            logger.info(f"✅ Initializing Groq LLM (model: {model_name})")
            _llm = ChatGroq(
                model=model_name,
                groq_api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        else:
            # Default to Gemini
            api_key = os.getenv("GOOGLE_API_KEY", "")
            if not api_key:
                logger.error("❌ GOOGLE_API_KEY is missing!")
                raise RuntimeError("GOOGLE_API_KEY not found in environment")

            model_name = os.getenv("LLM_MODEL", "gemini-2.0-flash")
            logger.info(f"✅ Initializing Gemini LLM (key starts with {api_key[:6]}...)")
            _llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
                max_retries=0,
            )
    return _llm


def call_llm_with_retry(prompt: str, retries: int = 6) -> str:
    """Call the configured LLM with exponential backoff for rate limits."""
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
                raise RuntimeError("LLM daily quota exhausted. Please try again tomorrow or upgrade your API key.")

            # Retry on rate limits (429) or service unavailability (503)
            if any(code in err for code in ["429", "503"]) or any(kw in err.lower() for kw in ["quota", "rate", "unavailable", "exhausted"]):
                base_wait = 2 ** attempt
                wait = min(base_wait + random.uniform(0, base_wait * 0.5), 30.0)
                logger.warning(f"LLM rate limit ({err[:60]}...). Retrying in {wait:.1f}s (attempt {attempt + 1}/{retries})")
                time.sleep(wait)
            else:
                logger.error(f"Non-retryable LLM error: {err}")
                raise
    raise RuntimeError("LLM call failed after max retries")


def count_tokens(text: str) -> int:
    """Rough token estimate (4 chars ≈ 1 token)."""
    return max(1, len(text) // 4)

