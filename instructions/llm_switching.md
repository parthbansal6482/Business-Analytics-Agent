# LLM Provider Switching Instructions

This project supports switching between **Google Gemini** and **OpenRouter** (which gives you access to models like Llama 3, Mistral, etc.).

## Prerequisites
1. **Google API Key**: For Gemini models.
2. **OpenRouter API Key**: Get one at [openrouter.ai](https://openrouter.ai/).

## Configuration

All configuration is done via your `.env` file in the **root** directory.

### 1. Using Gemini (Default)
To use Gemini 2.0 Flash directly:
```env
LLM_PROVIDER=gemini
GOOGLE_API_KEY=your_gemini_api_key_here
```

### 2. Using OpenRouter
To use OpenRouter (e.g., to access Free models or Llama 3):
```env
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your_openrouter_api_key_here
### 3. Using Groq (Highly Recommended for Free Tier)
Groq is blazingly fast and has a generous free tier. Get a key at [console.groq.com](https://console.groq.com/).
```env
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key_here
# Optional: Specify the model (Default is llama-3.3-70b-versatile)
GROQ_MODEL=llama-3.3-70b-versatile 
```

## How Switching Works
The application reads the `LLM_PROVIDER` variable at startup (`gemini`, `openrouter`, or `groq`).

## Troubleshooting
- **404 "No endpoints found" (OpenRouter)**: This often happens with `:free` models if the provider is down or your account settings are too restrictive.
    - **Fix 1**: Try a different free model like `google/gemma-2-9b-it:free`.
    - **Fix 2**: Log in to [OpenRouter Settings](https://openrouter.ai/settings/preferences) and ensure your **Data Policy** is NOT set to "Zero Data Retention (ZDR) only".
- **402 "Payment Required" (OpenRouter)**: Some "free" providers on OpenRouter still require a credit card on file or a non-zero balance. Switch to **Groq** if you want a truly $0 experience.
- **Missing Keys**: If you switch provider but forget to add the corresponding `_API_KEY`, the server will log an error.
