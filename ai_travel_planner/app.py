"""Main Streamlit application entry point for the Travel Planner."""

import argparse

import streamlit as st
from dotenv import load_dotenv

from ai_travel_planner.ui.config import PLANS_DIR, EXPORTS_DIR, IMAGES_DIR, DEBUG_DIR
from ai_travel_planner.ui.state import init_session_state
from ai_travel_planner.ui.tabs import (
    render_settings,
    render_sidebar,
    render_chat,
    render_itinerary_builder,
    render_blog_tips,
    render_pdf_export,
)

load_dotenv()


def parse_args():
    """Parse command-line arguments passed after -- in streamlit run."""
    parser = argparse.ArgumentParser(description="Travel Planner App")
    parser.add_argument(
        "--local",
        action="store_true",
        help="Run in local mode: load API keys from keyring/environment",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode: save itinerary debug output",
    )
    # Filter out streamlit arguments and parse only our app arguments
    args, _ = parser.parse_known_args()
    return args


# Parse arguments at module load time
APP_ARGS = parse_args()
LOCAL_MODE = APP_ARGS.local
DEBUG_MODE = APP_ARGS.debug

# Configure Streamlit page
st.set_page_config(
    page_title="Travel Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Create required directories
dirs_to_create = [PLANS_DIR, EXPORTS_DIR, IMAGES_DIR]
if DEBUG_MODE:
    dirs_to_create.append(DEBUG_DIR)
for d in dirs_to_create:
    d.mkdir(exist_ok=True)


def main():
    """Main application entry point."""
    init_session_state(LOCAL_MODE)
    render_sidebar(LOCAL_MODE, DEBUG_MODE)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["💬 Chat", "📋 Itinerary", "📄 PDF Export", "📝 Blog Tips", "⚙️ Settings"])

    with tab1:
        render_chat()

    with tab2:
        render_itinerary_builder(LOCAL_MODE, DEBUG_MODE)

    with tab3:
        render_pdf_export(LOCAL_MODE)

    with tab4:
        render_blog_tips()

    with tab5:
        render_settings(LOCAL_MODE)


if __name__ == "__main__":
    main()
