"""Sidebar renderer for the Travel Planner UI."""

import json

import streamlit as st

from ai_travel_planner.models import PlannerSession
from ai_travel_planner.ui.config import PROVIDERS, PROVIDER_MODELS
from ai_travel_planner.ui.api_keys import get_api_key, get_agent
from ai_travel_planner.ui.state import (
    sync_blog_content_from_session,
    sync_blog_content_to_session,
    sync_discovered_links_from_session,
    sync_discovered_links_to_session,
)
from ai_travel_planner.ui.helpers import get_app_title, render_settings_prompt


def render_sidebar(local_mode: bool, debug_mode: bool):
    """Render the sidebar with configuration options."""
    with st.sidebar:
        st.title(get_app_title(st.session_state.session))

        # Show mode indicators
        mode_parts = []
        if local_mode:
            mode_parts.append("Local")
        else:
            mode_parts.append("Remote")
        if debug_mode:
            mode_parts.append("Debug")
        mode_str = " | ".join(mode_parts)
        st.caption(f"Mode: {mode_str}")

        st.markdown("---")

        # Provider status display
        st.subheader("AI Provider")
        if st.session_state.agent:
            provider = st.session_state.session.ai_provider
            model = st.session_state.agent.model_id
            st.success(f"{provider} ({model})")
        else:
            render_settings_prompt("Not connected.")

        st.markdown("---")
        st.subheader("Save/Load Plans")

        # Load session via file upload (supports drag-and-drop)
        uploaded_file = st.file_uploader(
            "Load session",
            type=["json"],
            help="Upload a previously saved session JSON file (or drag & drop)",
            key="session_upload",
        )
        if uploaded_file is not None:
            # Track which file was last loaded to prevent re-loading on rerun
            file_id = f"{uploaded_file.name}_{uploaded_file.size}"
            if st.session_state.get("last_loaded_file") != file_id:
                try:
                    data = json.load(uploaded_file)
                    loaded = PlannerSession.model_validate(data)
                    st.session_state.session = loaded
                    st.session_state.last_loaded_file = file_id
                    # Restore blog content and discovered links from loaded session
                    sync_blog_content_from_session()
                    sync_discovered_links_from_session()

                    # Try to auto-connect to AI provider if key is available
                    provider = loaded.ai_provider
                    if provider not in PROVIDERS:
                        provider = PROVIDERS[0]
                    api_key = get_api_key(provider, local_mode)
                    if api_key:
                        default_model = PROVIDER_MODELS[provider][0]
                        st.session_state.agent = get_agent(provider, api_key, default_model)
                        if st.session_state.agent:
                            st.session_state.agent.set_language(loaded.language)
                            # Restore destinations to agent if available
                            if loaded.destinations and loaded.destinations.primary:
                                st.session_state.agent.set_destinations(loaded.destinations)
                            st.success(f"Loaded: {uploaded_file.name} - Connected to {provider}")
                        else:
                            st.success(f"Loaded: {uploaded_file.name}")
                    else:
                        st.session_state.agent = None
                        st.success(f"Loaded: {uploaded_file.name}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to load session: {e}")

        # Save session via download button
        st.markdown("**Save current session:**")
        save_name = st.text_input("Filename", placeholder="my_trip", key="save_name")
        # Sync blog content and discovered links before saving
        sync_blog_content_to_session()
        sync_discovered_links_to_session()
        session_json = st.session_state.session.model_dump_json(indent=2)
        # Use entered name, or generate default from destination/date
        if save_name:
            filename = f"session_{save_name}.json" if not save_name.endswith(".json") else save_name
        else:
            # Default filename based on destination or generic
            dest = st.session_state.session.destinations
            if dest and dest.primary:
                default_name = dest.primary.name.lower().replace(" ", "_")
            else:
                default_name = "trip"
            filename = f"session_{default_name}.json"
        st.download_button(
            "💾 Download Session",
            data=session_json,
            file_name=filename,
            mime="application/json",
            key="save_session_download",
        )
