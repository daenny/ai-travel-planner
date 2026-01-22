"""UI helper functions for the Travel Planner."""

import json
from pathlib import Path

import streamlit as st

from ai_travel_planner.models import PlannerSession, Itinerary
from ai_travel_planner.agents.base import TravelAgent
from ai_travel_planner.services import UnsplashService
from ai_travel_planner.services.destination_detector import DestinationDetector

from .config import DEBUG_DIR, IMAGES_DIR
from .api_keys import get_api_key


def get_app_title(session: PlannerSession) -> str:
    """Get dynamic title based on detected destination."""
    dest_name = session.destinations.display_name()
    if dest_name and dest_name != "Your Trip":
        return f"✈️ {dest_name} Planner"
    return "✈️ Travel Planner"


def get_chat_placeholder(session: PlannerSession) -> str:
    """Get dynamic chat input placeholder based on destination."""
    dest_name = session.destinations.display_name()
    if dest_name and dest_name != "Your Trip":
        return f"Ask about your {dest_name} trip..."
    return "Where would you like to travel?"


def render_settings_prompt(message: str, key: str, use_columns: bool = True):
    """Render a message with a 'Go to Settings' button.

    Args:
        message: Info/warning message to display
        key: Unique key for the button
        use_columns: If True, use columns layout; if False, stack vertically (for sidebar)
    """
    if use_columns:
        col_msg, col_btn = st.columns([3, 1])
        with col_msg:
            st.info(message)
        with col_btn:
            if st.button("⚙️ Go to Settings", key=key, use_container_width=True):
                st.session_state.navigate_to_settings = True
                st.rerun()
    else:
        st.caption(message)
        if st.button("⚙️ Go to Settings", key=key, use_container_width=True):
            st.session_state.navigate_to_settings = True
            st.rerun()


def save_debug_output(itinerary: Itinerary, chat_context: str, mode: str, debug_mode: bool, **extra_fields):
    """Save debug output for itinerary generation if DEBUG_MODE is enabled."""
    if not debug_mode:
        return
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_file = DEBUG_DIR / f"itinerary_debug_{timestamp}.json"
    debug_data = {
        "timestamp": timestamp,
        "chat_context": chat_context,
        "language": st.session_state.session.language,
        "generation_mode": mode,
        "itinerary": itinerary.model_dump(mode="json"),
        **extra_fields,
    }
    with open(debug_file, "w") as f:
        json.dump(debug_data, f, indent=2, default=str)
    st.info(f"Debug output saved to {debug_file}")


def maybe_update_destination(session: PlannerSession, agent: TravelAgent) -> bool:
    """Check if we should update detected destination."""
    # Only detect if no destination set yet
    if session.destinations.primary is None:
        detector = DestinationDetector()
        # Check last few messages for destination patterns
        last_messages = session.chat_history[-3:]
        for msg in last_messages:
            if msg.role == "user":
                simple_dest = detector.extract_from_text(msg.content)
                if simple_dest:
                    # Quick detection found something - do full AI extraction
                    new_destinations = detector.extract_from_conversation(
                        session.chat_history, agent
                    )
                    if new_destinations.primary:
                        session.destinations = new_destinations
                        agent.set_destinations(new_destinations)
                        return True
    return False


def get_blog_context() -> str:
    """Build context string from extracted blog content."""
    if not st.session_state.blog_content:
        return ""

    parts = [
        "## Reference Information from Travel Blogs",
        "The user has provided these travel blogs as references. Use this information to give better recommendations:\n"
    ]

    for url, content in st.session_state.blog_content.items():
        parts.append(content.to_context_string())
        parts.append("")

    return "\n".join(parts)


def load_photos_for_itinerary(itinerary: Itinerary, local_mode: bool) -> bool:
    """Load photos for days with image_queries but no image_paths."""
    unsplash_key = get_api_key("Unsplash", local_mode)
    if not unsplash_key:
        st.warning("Unsplash API key not configured. Add it in Settings.")
        return False

    unsplash = UnsplashService(unsplash_key, IMAGES_DIR)
    days_needing_photos = [d for d in itinerary.days if d.image_queries and not d.image_paths]

    if not days_needing_photos:
        return False

    progress = st.progress(0)
    status = st.empty()

    for i, day in enumerate(days_needing_photos):
        status.text(f"Loading photos for Day {day.day_number}...")
        paths = unsplash.download_photos_for_queries(day.image_queries, max_images=3)
        if paths:
            day.image_paths = [str(p) for p in paths]
            day.image_path = str(paths[0]) if not day.image_path else day.image_path
        progress.progress((i + 1) / len(days_needing_photos))

    progress.empty()
    status.empty()
    return True
