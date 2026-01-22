"""Settings tab renderer for the Travel Planner UI."""

import streamlit as st

from ai_travel_planner.ui.config import PROVIDERS, PROVIDER_MODELS, SUPPORTED_LANGUAGES
from ai_travel_planner.ui.api_keys import (
    get_api_key,
    get_api_key_from_session,
    get_system_api_key,
    save_api_key,
    save_api_key_to_session,
    delete_api_key,
    get_agent,
)


def render_settings(local_mode: bool):
    """Render the settings tab with AI provider, language, and API key configuration."""
    st.header("⚙️ Settings")

    # AI Provider section
    st.subheader("AI Provider")

    # Use session.ai_provider as source of truth for initial index
    current_provider = st.session_state.session.ai_provider
    if current_provider not in PROVIDERS:
        current_provider = PROVIDERS[0]
    provider_index = PROVIDERS.index(current_provider)

    provider = st.selectbox(
        "Select AI Provider",
        PROVIDERS,
        index=provider_index,
        key="settings_provider_select",
    )

    # Get current model for this provider (if agent exists and matches)
    current_model = None
    if st.session_state.agent and st.session_state.session.ai_provider == provider:
        current_model = st.session_state.agent.model_id

    # Find model index
    models = PROVIDER_MODELS[provider]
    model_index = 0
    if current_model and current_model in models:
        model_index = models.index(current_model)

    model = st.selectbox(
        "Select Model",
        models,
        index=model_index,
        key=f"settings_model_select_{provider}",
    )

    # Load API key from keyring or environment
    stored_key = get_api_key(provider, local_mode)
    api_key = st.text_input(
        f"{provider} API Key",
        value=stored_key,
        type="password",
        key=f"settings_api_key_{provider}",
    )

    # Save/delete key buttons (different behavior in local vs remote mode)
    if local_mode:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Key", key=f"settings_save_key_{provider}", use_container_width=True):
                if api_key:
                    if save_api_key(provider, api_key, local_mode):
                        st.success("Key saved!")
                    else:
                        st.error("Failed to save")
        with col2:
            if st.button("🗑️ Delete", key=f"settings_del_key_{provider}", use_container_width=True):
                if delete_api_key(provider, local_mode):
                    st.success("Key deleted!")
                    st.rerun()
    else:
        # Remote mode: only save user-entered keys, not system keys from secrets/env
        system_key = get_system_api_key(provider)
        if api_key and api_key != get_api_key_from_session(provider) and api_key != system_key:
            save_api_key_to_session(provider, api_key)
        st.caption("Keys are stored in session (save session to persist)")

    # Check if settings differ from current agent
    agent_provider = st.session_state.session.ai_provider
    agent_model = st.session_state.agent.model_id if st.session_state.agent else None
    settings_changed = (provider != agent_provider or model != agent_model)

    # Show current status and connect button
    if st.session_state.agent and not settings_changed:
        st.success(f"Connected to {agent_provider} ({agent_model})")
    elif api_key:
        if st.button("Connect", key="connect_provider", type="primary", use_container_width=True):
            st.session_state.agent = get_agent(provider, api_key, model)
            st.session_state.session.ai_provider = provider
            if st.session_state.agent:
                st.session_state.agent.set_language(st.session_state.session.language)
                st.rerun()
            else:
                st.error(f"Failed to connect to {provider}")
        if settings_changed:
            st.info(f"Click Connect to switch to {provider} ({model})")
    else:
        st.warning(f"Enter an API key for {provider}")

    st.markdown("---")

    # Language section
    st.subheader("Language")
    current_language = st.session_state.session.language
    language_index = SUPPORTED_LANGUAGES.index(current_language) if current_language in SUPPORTED_LANGUAGES else 0
    language = st.selectbox(
        "Content Language",
        SUPPORTED_LANGUAGES,
        index=language_index,
        key="settings_language_select",
        help="Language for AI-generated content (descriptions, tips, activities)"
    )
    if language != st.session_state.session.language:
        st.session_state.session.language = language
        if st.session_state.agent:
            st.session_state.agent.set_language(language)

    st.markdown("---")

    # Unsplash section
    st.subheader("Unsplash Images")
    stored_unsplash = get_api_key("Unsplash", local_mode)
    unsplash_key_input = st.text_input(
        "Unsplash Access Key",
        value=stored_unsplash,
        type="password",
        key="settings_unsplash_key",
    )
    if local_mode:
        if st.button("💾 Save Unsplash Key", key="settings_save_unsplash"):
            unsplash_val = st.session_state.get("settings_unsplash_key", "")
            if unsplash_val:
                if save_api_key("Unsplash", unsplash_val, local_mode):
                    st.success("Unsplash key saved!")
                else:
                    st.error("Failed to save")
    else:
        # Remote mode: only save user-entered keys, not system keys from secrets/env
        system_unsplash = get_system_api_key("Unsplash")
        if unsplash_key_input and unsplash_key_input != get_api_key_from_session("Unsplash") and unsplash_key_input != system_unsplash:
            save_api_key_to_session("Unsplash", unsplash_key_input)

    st.caption("Unsplash API key is used to fetch travel images for your PDF itinerary.")
