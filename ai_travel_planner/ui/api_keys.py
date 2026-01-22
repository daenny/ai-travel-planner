"""API key management functions for the Travel Planner UI."""

import os

import keyring
import streamlit as st

from ai_travel_planner.agents import ClaudeAgent, OpenAIAgent, GeminiAgent
from ai_travel_planner.agents.base import TravelAgent

from .config import (
    KEYRING_SERVICE,
    KEYRING_KEYS,
    ENV_VAR_KEYS,
    PROVIDERS,
    PROVIDER_MODELS,
)


def get_api_key_from_session(provider: str) -> str:
    """Get API key from the current session (for remote mode)."""
    if "session" not in st.session_state:
        return ""
    api_keys = st.session_state.session.api_keys
    provider_map = {
        "Claude": api_keys.anthropic,
        "OpenAI": api_keys.openai,
        "Gemini": api_keys.google,
        "Unsplash": api_keys.unsplash,
    }
    return provider_map.get(provider, "")


def save_api_key_to_session(provider: str, api_key: str) -> None:
    """Save API key to the current session (for remote mode)."""
    if "session" not in st.session_state:
        return
    api_keys = st.session_state.session.api_keys
    if provider == "Claude":
        api_keys.anthropic = api_key
    elif provider == "OpenAI":
        api_keys.openai = api_key
    elif provider == "Gemini":
        api_keys.google = api_key
    elif provider == "Unsplash":
        api_keys.unsplash = api_key


def get_api_key(provider: str, local_mode: bool) -> str:
    """Get API key based on deployment mode.

    Local mode: Load from keyring, fall back to environment variables.
    Remote mode: Load from Streamlit secrets, fall back to environment variables,
                 then session (user-entered keys).
    """
    env_var = ENV_VAR_KEYS.get(provider, "")

    if not local_mode:
        # Remote mode: check Streamlit secrets first
        try:
            if hasattr(st, "secrets") and env_var in st.secrets:
                return st.secrets[env_var]
        except Exception:
            pass

        # Then check environment variables (for container deployments)
        env_key = os.getenv(env_var, "")
        if env_key:
            return env_key

        # Finally fall back to session-stored keys
        return get_api_key_from_session(provider)

    # Local mode: keyring first, then environment variables
    key_name = KEYRING_KEYS.get(provider, "")

    # Try keyring first
    try:
        key = keyring.get_password(KEYRING_SERVICE, key_name)
        if key:
            return key
    except Exception:
        pass

    # Fall back to environment variables
    return os.getenv(env_var, "")


def get_system_api_key(provider: str) -> str:
    """Get API key from system sources only (secrets/env), NOT from session.

    Used to detect if a key is system-provided vs user-entered.
    """
    env_var = ENV_VAR_KEYS.get(provider, "")

    # Check Streamlit secrets first
    try:
        if hasattr(st, "secrets") and env_var in st.secrets:
            return st.secrets[env_var]
    except Exception:
        pass

    # Then check environment variables
    return os.getenv(env_var, "")


def save_api_key(provider: str, api_key: str, local_mode: bool) -> bool:
    """Save API key based on deployment mode.

    Local mode: Save to keyring.
    Remote mode: Save to session (will be persisted when session is saved).
    """
    if not api_key:
        return False

    if not local_mode:
        # Remote mode: save to session
        save_api_key_to_session(provider, api_key)
        return True

    # Local mode: save to keyring
    key_name = KEYRING_KEYS.get(provider, "")
    if not key_name:
        return False

    try:
        keyring.set_password(KEYRING_SERVICE, key_name, api_key)
        return True
    except Exception:
        return False


def delete_api_key(provider: str, local_mode: bool) -> bool:
    """Delete API key based on deployment mode.

    Local mode: Delete from keyring.
    Remote mode: Clear from session.
    """
    if not local_mode:
        # Remote mode: clear from session
        save_api_key_to_session(provider, "")
        return True

    # Local mode: delete from keyring
    key_name = KEYRING_KEYS.get(provider, "")
    if not key_name:
        return False

    try:
        keyring.delete_password(KEYRING_SERVICE, key_name)
        return True
    except Exception:
        return False


def auto_detect_provider(local_mode: bool) -> str | None:
    """Auto-detect first available provider with an API key."""
    for provider in PROVIDERS:
        if get_api_key(provider, local_mode):
            return provider
    return None


def get_agent(provider: str, api_key: str, model: str) -> TravelAgent | None:
    """Create an agent for the selected provider."""
    try:
        if provider == "Claude":
            return ClaudeAgent(api_key, model=model)
        elif provider == "OpenAI":
            return OpenAIAgent(api_key, model=model)
        elif provider == "Gemini":
            return GeminiAgent(api_key, model=model)
    except Exception as e:
        st.error(f"Failed to initialize {provider} agent: {e}")
    return None
