"""Configuration constants for the Travel Planner UI."""

from pathlib import Path

# AI Provider configuration
PROVIDERS = ["Claude", "OpenAI", "Gemini"]

PROVIDER_MODELS = {
    "Claude": [
        "claude-sonnet-4-5",
        "claude-opus-4-5",
        "claude-haiku-4-5",
        "claude-opus-4-1",
        "claude-sonnet-4",
    ],
    "OpenAI": [
        "gpt-5.2",
        "gpt-5.2-pro",
        "gpt-5-mini",
        "gpt-5-nano",
        "o3",
        "o4-mini",
        "gpt-5-search-api",
        "gpt-4.1",
        "gpt-4o",
        "gpt-4o-mini",
    ],
    "Gemini": [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.5-pro",
        "gemini-3-pro-preview",
    ],
}

SUPPORTED_LANGUAGES = [
    "English",
    "Spanish",
    "French",
    "German",
    "Italian",
    "Portuguese",
    "Dutch",
    "Japanese",
    "Chinese (Simplified)",
    "Korean",
]

# Directory paths
PLANS_DIR = Path("plans")
EXPORTS_DIR = Path("exports")
IMAGES_DIR = Path("images")
DEBUG_DIR = Path("debug")

# Keyring service name for storing API keys
KEYRING_SERVICE = "travel-planner"

# Mapping of providers to keyring key names
KEYRING_KEYS = {
    "Claude": "anthropic_api_key",
    "OpenAI": "openai_api_key",
    "Gemini": "google_api_key",
    "Unsplash": "unsplash_access_key",
}

# Mapping of providers to environment variable names
ENV_VAR_KEYS = {
    "Claude": "ANTHROPIC_API_KEY",
    "OpenAI": "OPENAI_API_KEY",
    "Gemini": "GOOGLE_API_KEY",
    "Unsplash": "UNSPLASH_ACCESS_KEY",
}
