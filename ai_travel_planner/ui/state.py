"""Session state management for the Travel Planner UI."""

import streamlit as st

from ai_travel_planner.models import (
    PlannerSession,
    SavedBlogContent,
    SavedDiscoveredLink,
    GenerationState,
)
from ai_travel_planner.services.blog_scraper import BlogContent, DiscoveredLink

from .config import PROVIDER_MODELS
from .api_keys import auto_detect_provider, get_api_key, get_agent


def blog_content_to_saved(content: BlogContent) -> SavedBlogContent:
    """Convert BlogContent dataclass to SavedBlogContent Pydantic model."""
    return SavedBlogContent(
        url=content.url,
        title=content.title,
        summary=content.summary,
        tips=content.tips,
        highlights=content.highlights,
        images=content.images,
        raw_text=content.raw_text,
    )


def saved_to_blog_content(saved: SavedBlogContent) -> BlogContent:
    """Convert SavedBlogContent Pydantic model to BlogContent dataclass."""
    return BlogContent(
        url=saved.url,
        title=saved.title,
        summary=saved.summary,
        tips=saved.tips,
        highlights=saved.highlights,
        images=saved.images,
        raw_text=saved.raw_text,
    )


def sync_blog_content_to_session():
    """Sync st.session_state.blog_content to session.blog_content for saving."""
    st.session_state.session.blog_content = {
        url: blog_content_to_saved(content)
        for url, content in st.session_state.blog_content.items()
    }


def sync_blog_content_from_session():
    """Sync session.blog_content to st.session_state.blog_content after loading."""
    st.session_state.blog_content = {
        url: saved_to_blog_content(saved)
        for url, saved in st.session_state.session.blog_content.items()
    }


def discovered_link_to_saved(link: DiscoveredLink) -> SavedDiscoveredLink:
    """Convert DiscoveredLink dataclass to SavedDiscoveredLink Pydantic model."""
    return SavedDiscoveredLink(
        url=link.url,
        title=link.title,
        source_url=link.source_url,
    )


def saved_to_discovered_link(saved: SavedDiscoveredLink) -> DiscoveredLink:
    """Convert SavedDiscoveredLink Pydantic model to DiscoveredLink dataclass."""
    return DiscoveredLink(
        url=saved.url,
        title=saved.title,
        source_url=saved.source_url,
    )


def sync_discovered_links_to_session():
    """Sync st.session_state.discovered_links to session.discovered_links for saving."""
    st.session_state.session.discovered_links = {
        source_url: [discovered_link_to_saved(link) for link in links]
        for source_url, links in st.session_state.discovered_links.items()
    }


def sync_discovered_links_from_session():
    """Sync session.discovered_links to st.session_state.discovered_links after loading."""
    st.session_state.discovered_links = {
        source_url: [saved_to_discovered_link(saved) for saved in saved_links]
        for source_url, saved_links in st.session_state.session.discovered_links.items()
    }


def init_session_state(local_mode: bool):
    """Initialize session state variables."""
    if "session" not in st.session_state:
        st.session_state.session = PlannerSession()
    if "agent" not in st.session_state:
        st.session_state.agent = None
    if "blog_content" not in st.session_state:
        st.session_state.blog_content = {}
    if "discovered_links" not in st.session_state:
        st.session_state.discovered_links = {}
    if "generation_state" not in st.session_state:
        st.session_state.generation_state = GenerationState()
    if "pending_diff" not in st.session_state:
        st.session_state.pending_diff = None
    if "navigate_to_settings" not in st.session_state:
        st.session_state.navigate_to_settings = False

    # Auto-detect and initialize provider on first load
    if "auto_detected" not in st.session_state:
        st.session_state.auto_detected = True
        detected_provider = auto_detect_provider(local_mode)
        if detected_provider:
            api_key = get_api_key(detected_provider, local_mode)
            default_model = PROVIDER_MODELS[detected_provider][0]
            st.session_state.agent = get_agent(detected_provider, api_key, default_model)
            st.session_state.session.ai_provider = detected_provider
            if st.session_state.agent:
                st.session_state.agent.set_language(st.session_state.session.language)
