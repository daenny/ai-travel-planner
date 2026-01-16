import argparse
import json
import os
import sys
from pathlib import Path

import keyring
import streamlit as st
from dotenv import load_dotenv

from ai_travel_planner.models import ChatMessage, Itinerary, ItineraryMetadata, PlannerSession, SavedBlogContent, TripDestinations, GenerationProgress, GenerationState
from ai_travel_planner.agents import ClaudeAgent, OpenAIAgent, GeminiAgent
from ai_travel_planner.agents.base import TravelAgent
from ai_travel_planner.services import UnsplashService, BlogScraper, PDFGenerator, generate_itinerary_iteratively, resume_itinerary_generation
from ai_travel_planner.services.pdf_generator import PDFStyle
from ai_travel_planner.services.blog_scraper import BlogContent
from ai_travel_planner.services.destination_detector import DestinationDetector

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

# Keyring service name for storing API keys
KEYRING_SERVICE = "travel-planner"

# Mapping of providers to keyring key names
KEYRING_KEYS = {
    "Claude": "anthropic_api_key",
    "OpenAI": "openai_api_key",
    "Gemini": "google_api_key",
    "Unsplash": "unsplash_access_key",
}


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


# Mapping of providers to environment variable names
ENV_VAR_KEYS = {
    "Claude": "ANTHROPIC_API_KEY",
    "OpenAI": "OPENAI_API_KEY",
    "Gemini": "GOOGLE_API_KEY",
    "Unsplash": "UNSPLASH_ACCESS_KEY",
}


def get_api_key(provider: str) -> str:
    """Get API key based on deployment mode.

    Local mode: Load from keyring, fall back to environment variables.
    Remote mode: Load from Streamlit secrets, fall back to environment variables,
                 then session (user-entered keys).
    """
    env_var = ENV_VAR_KEYS.get(provider, "")

    if not LOCAL_MODE:
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


def save_api_key(provider: str, api_key: str) -> bool:
    """Save API key based on deployment mode.

    Local mode: Save to keyring.
    Remote mode: Save to session (will be persisted when session is saved).
    """
    if not api_key:
        return False

    if not LOCAL_MODE:
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


def delete_api_key(provider: str) -> bool:
    """Delete API key based on deployment mode.

    Local mode: Delete from keyring.
    Remote mode: Clear from session.
    """
    if not LOCAL_MODE:
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


def auto_detect_provider() -> str | None:
    """Auto-detect first available provider with an API key."""
    for provider in PROVIDERS:
        if get_api_key(provider):
            return provider
    return None


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


st.set_page_config(
    page_title="Travel Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

PLANS_DIR = Path("plans")
EXPORTS_DIR = Path("exports")
IMAGES_DIR = Path("images")
DEBUG_DIR = Path("debug")

dirs_to_create = [PLANS_DIR, EXPORTS_DIR, IMAGES_DIR]
if DEBUG_MODE:
    dirs_to_create.append(DEBUG_DIR)
for d in dirs_to_create:
    d.mkdir(exist_ok=True)


def init_session_state():
    """Initialize session state variables."""
    if "session" not in st.session_state:
        st.session_state.session = PlannerSession()
    if "agent" not in st.session_state:
        st.session_state.agent = None
    if "blog_content" not in st.session_state:
        st.session_state.blog_content = {}
    if "generation_state" not in st.session_state:
        st.session_state.generation_state = GenerationState()

    # Auto-detect and initialize provider on first load
    if "auto_detected" not in st.session_state:
        st.session_state.auto_detected = True
        detected_provider = auto_detect_provider()
        if detected_provider:
            api_key = get_api_key(detected_provider)
            default_model = PROVIDER_MODELS[detected_provider][0]
            st.session_state.agent = get_agent(detected_provider, api_key, default_model)
            st.session_state.session.ai_provider = detected_provider
            if st.session_state.agent:
                st.session_state.agent.set_language(st.session_state.session.language)


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


def render_settings():
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
    stored_key = get_api_key(provider)
    api_key = st.text_input(
        f"{provider} API Key",
        value=stored_key,
        type="password",
        key=f"settings_api_key_{provider}",
    )

    # Save/delete key buttons (different behavior in local vs remote mode)
    if LOCAL_MODE:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Key", key=f"settings_save_key_{provider}", use_container_width=True):
                if api_key:
                    if save_api_key(provider, api_key):
                        st.success("Key saved!")
                    else:
                        st.error("Failed to save")
        with col2:
            if st.button("🗑️ Delete", key=f"settings_del_key_{provider}", use_container_width=True):
                if delete_api_key(provider):
                    st.success("Key deleted!")
                    st.rerun()
    else:
        # Remote mode: save to session automatically when key is entered
        if api_key and api_key != get_api_key_from_session(provider):
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
    stored_unsplash = get_api_key("Unsplash")
    unsplash_key_input = st.text_input(
        "Unsplash Access Key",
        value=stored_unsplash,
        type="password",
        key="settings_unsplash_key",
    )
    if LOCAL_MODE:
        if st.button("💾 Save Unsplash Key", key="settings_save_unsplash"):
            unsplash_val = st.session_state.get("settings_unsplash_key", "")
            if unsplash_val:
                if save_api_key("Unsplash", unsplash_val):
                    st.success("Unsplash key saved!")
                else:
                    st.error("Failed to save")
    else:
        # Remote mode: save to session automatically
        if unsplash_key_input and unsplash_key_input != get_api_key_from_session("Unsplash"):
            save_api_key_to_session("Unsplash", unsplash_key_input)

    st.caption("Unsplash API key is used to fetch travel images for your PDF itinerary.")


def render_sidebar():
    """Render the sidebar with configuration options."""
    with st.sidebar:
        st.title(get_app_title(st.session_state.session))

        # Show mode indicators
        mode_parts = []
        if LOCAL_MODE:
            mode_parts.append("Local")
        else:
            mode_parts.append("Remote")
        if DEBUG_MODE:
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
            st.warning("No AI provider configured")
            st.caption("Go to Settings tab to configure")

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
                    # Restore blog content from loaded session
                    sync_blog_content_from_session()
                    # Clear agent so user can reconnect with loaded provider
                    st.session_state.agent = None
                    st.success(f"Loaded: {uploaded_file.name} ({len(st.session_state.blog_content)} blogs)")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to load session: {e}")

        # Save session via download button
        st.markdown("**Save current session:**")
        save_name = st.text_input("Filename", placeholder="my_trip", key="save_name")
        # Sync blog content before saving
        sync_blog_content_to_session()
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

        st.markdown("---")
        st.subheader("Generate PDF")

        pdf_style = st.selectbox(
            "PDF Style",
            [s.value for s in PDFStyle],
            format_func=lambda x: x.title(),
            key="pdf_style",
        )

        if st.button("Generate PDF", key="gen_pdf"):
            if st.session_state.session.itinerary.days:
                with st.spinner("Generating PDF..."):
                    unsplash_api_key = get_api_key("Unsplash")
                    if unsplash_api_key:
                        unsplash = UnsplashService(unsplash_api_key, IMAGES_DIR)
                        for day in st.session_state.session.itinerary.days:
                            # Use AI-generated image queries if available
                            if day.image_queries and not day.image_paths:
                                paths = unsplash.download_photos_for_queries(
                                    day.image_queries, max_images=3
                                )
                                day.image_paths = [str(p) for p in paths]
                                # Also set single image_path for backward compatibility
                                if paths and not day.image_path:
                                    day.image_path = str(paths[0])
                            # Fallback to location-based single image
                            elif not day.image_path and not day.image_paths:
                                img_path = unsplash.get_photo_for_location(day.location)
                                if img_path:
                                    day.image_path = str(img_path)
                                    day.image_paths = [str(img_path)]

                    generator = PDFGenerator(exports_dir=EXPORTS_DIR)
                    pdf_path = generator.generate_pdf(
                        st.session_state.session.itinerary,
                        PDFStyle(pdf_style),
                    )
                    st.success(f"PDF generated!")

                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            "Download PDF",
                            f,
                            file_name=pdf_path.name,
                            mime="application/pdf",
                        )
            else:
                st.warning("Create an itinerary first!")

        if st.button("Generate All Styles", key="gen_all_pdf"):
            if st.session_state.session.itinerary.days:
                with st.spinner("Generating all PDFs..."):
                    generator = PDFGenerator(exports_dir=EXPORTS_DIR)
                    paths = generator.generate_all_styles(st.session_state.session.itinerary)
                    st.success("All PDFs generated!")
                    for style, path in paths.items():
                        with open(path, "rb") as f:
                            st.download_button(
                                f"Download {style.value.title()}",
                                f,
                                file_name=path.name,
                                mime="application/pdf",
                                key=f"dl_{style.value}",
                            )


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


def render_chat():
    """Render the chat interface."""
    st.header("💬 Plan Your Trip")

    # Check if AI provider is configured
    has_agent = st.session_state.agent is not None

    if not has_agent:
        st.warning("⚠️ No AI provider configured. Go to the **Settings** tab to set up an API key.")

    # Chat input at the top (disabled if no agent)
    chat_placeholder = get_chat_placeholder(st.session_state.session)
    prompt = st.chat_input(chat_placeholder, disabled=not has_agent)

    # Show blog context indicator and share button
    if st.session_state.blog_content:
        blog_count = len(st.session_state.blog_content)
        total_tips = sum(len(c.tips) for c in st.session_state.blog_content.values())

        col1, col2 = st.columns([3, 1])
        with col1:
            st.info(f"📚 {blog_count} blog(s) with {total_tips} tips available")
        with col2:
            if st.button("Share tips with AI", key="share_blog_tips"):
                if st.session_state.agent:
                    blog_context = get_blog_context()
                    share_msg = f"I've gathered tips from travel blogs for reference:\n\n{blog_context}\n\nPlease acknowledge you've received these tips and use them to help plan my trip."
                    st.session_state.session.chat_history.append(
                        ChatMessage(role="user", content="[Shared blog tips with AI]")
                    )
                    # Get AI acknowledgment
                    with st.chat_message("assistant"):
                        response_placeholder = st.empty()
                        full_response = ""
                        for chunk in st.session_state.agent.chat(
                            share_msg, st.session_state.session.chat_history[:-1]
                        ):
                            full_response += chunk
                            response_placeholder.markdown(full_response + "▌")
                        response_placeholder.markdown(full_response)
                        st.session_state.session.chat_history.append(
                            ChatMessage(role="assistant", content=full_response)
                        )
                    st.rerun()

    # Handle new message input
    if prompt:
        st.session_state.session.chat_history.append(
            ChatMessage(role="user", content=prompt)
        )

        if st.session_state.agent:
            response_placeholder = st.empty()
            full_response = ""

            try:
                history = st.session_state.session.chat_history[:-1]

                for chunk in st.session_state.agent.chat(prompt, history):
                    full_response += chunk
                    response_placeholder.markdown(full_response + "▌")

                response_placeholder.empty()
                st.session_state.session.chat_history.append(
                    ChatMessage(role="assistant", content=full_response)
                )

                # Try to detect destination after user message
                if maybe_update_destination(st.session_state.session, st.session_state.agent):
                    st.rerun()  # Refresh to show updated title
                else:
                    st.rerun()  # Rerun to display the new messages in correct order

            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning("Please configure an AI provider in the sidebar.")
            st.rerun()

    # Display messages in reverse order (newest first)
    for msg in reversed(st.session_state.session.chat_history):
        with st.chat_message(msg.role):
            st.markdown(msg.content)


def load_photos_for_itinerary(itinerary: Itinerary) -> bool:
    """Load photos for days with image_queries but no image_paths."""
    unsplash_key = get_api_key("Unsplash")
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


def render_itinerary_builder():
    """Render the itinerary builder/viewer."""
    st.header("📋 Current Itinerary")

    itinerary = st.session_state.session.itinerary

    col1, col2 = st.columns([2, 1])
    with col1:
        itinerary.title = st.text_input("Trip Title", value=itinerary.title)
    with col2:
        itinerary.travelers = st.number_input(
            "Travelers", min_value=1, max_value=20, value=itinerary.travelers
        )

    itinerary.description = st.text_area(
        "Description", value=itinerary.description, height=80
    )

    st.markdown("---")

    if st.session_state.agent:
        st.subheader("Generate Itinerary from Chat")

        # Check if there's a resumable generation
        gen_state = st.session_state.generation_state
        can_resume = gen_state.can_resume and st.session_state.session.itinerary.days

        # Show resume banner if available
        if can_resume:
            st.warning(
                f"⚠️ Previous generation incomplete: {len(st.session_state.session.itinerary.days)}/{gen_state.progress.total_days} days generated. "
                f"Last error: {gen_state.progress.error_message or 'Unknown'}"
            )

        # Generation options
        col_opt1, col_opt2, col_opt3 = st.columns([1, 1, 2])
        with col_opt1:
            block_size = st.selectbox(
                "Days per block",
                options=[2, 3, 4],
                index=1,  # Default to 3
                key="gen_block_size",
                help="Number of days to generate at once. Smaller blocks show progress faster."
            )
        with col_opt2:
            use_iterative = st.checkbox(
                "Iterative mode",
                value=True,
                key="use_iterative",
                help="Generate days in blocks with progress feedback"
            )

        # Generate and Resume buttons
        col_btn1, col_btn2 = st.columns([1, 1])
        with col_btn1:
            generate_clicked = st.button("Create Itinerary", key="gen_itinerary", type="primary", use_container_width=True)
        with col_btn2:
            resume_clicked = st.button(
                f"Resume ({len(st.session_state.session.itinerary.days)}/{gen_state.progress.total_days if gen_state.progress else '?'} days)",
                key="resume_itinerary",
                disabled=not can_resume,
                use_container_width=True
            )

        # Handle generation
        if generate_clicked or resume_clicked:
            chat_context = "\n".join(
                f"{msg.role}: {msg.content}"
                for msg in st.session_state.session.chat_history
            )

            if use_iterative:
                # Iterative generation with progress
                progress_container = st.container()
                status_placeholder = progress_container.empty()
                progress_bar = progress_container.progress(0)
                days_display = progress_container.empty()
                error_placeholder = progress_container.empty()

                try:
                    is_resume = resume_clicked and can_resume

                    if is_resume:
                        status_placeholder.info(f"▶️ Resuming from day {len(st.session_state.session.itinerary.days) + 1}...")
                        generator = resume_itinerary_generation(
                            agent=st.session_state.agent,
                            requirements=gen_state.requirements,
                            metadata=gen_state.metadata,
                            existing_itinerary=st.session_state.session.itinerary,
                            language=gen_state.language,
                            block_size=block_size,
                        )
                    else:
                        status_placeholder.info("🚀 Starting generation...")
                        generator = generate_itinerary_iteratively(
                            agent=st.session_state.agent,
                            requirements=chat_context,
                            language=st.session_state.session.language,
                            block_size=block_size,
                        )

                    final_itinerary = None
                    final_metadata = None
                    final_progress = None

                    for progress, partial_itinerary, metadata in generator:
                        final_progress = progress
                        final_metadata = metadata

                        # Update progress display
                        if progress.status == "generating_metadata":
                            status_placeholder.info("⏳ Generating trip overview...")
                            progress_bar.progress(0)

                        elif progress.status == "generating_days":
                            pct = progress.completed_days / progress.total_days if progress.total_days > 0 else 0
                            progress_bar.progress(pct)

                            # Cleaner status: "Generating days 4-6 of 21"
                            if progress.current_block_start > 0:
                                status_placeholder.info(
                                    f"⏳ Generating days {progress.current_block_start}-{progress.current_block_end} of {progress.total_days}"
                                )

                            # Show completed days separately below progress bar
                            if partial_itinerary.days:
                                with days_display.container():
                                    st.caption(f"✓ {progress.completed_days} days complete")
                                    # Show last 3 generated days
                                    for day in partial_itinerary.days[-3:]:
                                        st.markdown(f"  Day {day.day_number}: {day.title}")

                        elif progress.status == "complete":
                            progress_bar.progress(1.0)
                            status_placeholder.success(f"✅ Complete! {progress.total_days} days generated.")
                            days_display.empty()
                            final_itinerary = partial_itinerary
                            # Clear generation state on success
                            st.session_state.generation_state = GenerationState()

                        elif progress.status in ("error", "partial"):
                            pct = progress.completed_days / progress.total_days if progress.total_days > 0 else 0
                            progress_bar.progress(pct)

                            if progress.completed_days > 0:
                                # Partial completion - can resume
                                status_placeholder.warning(
                                    f"⚠️ Stopped at {progress.completed_days}/{progress.total_days} days"
                                )
                                error_placeholder.error(f"Error: {progress.error_message}")
                                final_itinerary = partial_itinerary

                                # Store state for resume
                                st.session_state.generation_state = GenerationState(
                                    requirements=chat_context if not is_resume else gen_state.requirements,
                                    language=st.session_state.session.language if not is_resume else gen_state.language,
                                    block_size=block_size,
                                    metadata=metadata,
                                    progress=progress,
                                )
                            else:
                                # Complete failure
                                status_placeholder.error("❌ Generation failed")
                                error_placeholder.error(f"Error: {progress.error_message}")
                            break

                    if final_itinerary:
                        st.session_state.session.itinerary = final_itinerary

                        # Save debug output if debug mode is enabled
                        if DEBUG_MODE:
                            from datetime import datetime
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            debug_file = DEBUG_DIR / f"itinerary_debug_{timestamp}.json"
                            debug_data = {
                                "timestamp": timestamp,
                                "chat_context": chat_context,
                                "language": st.session_state.session.language,
                                "generation_mode": "iterative" + ("_resume" if is_resume else ""),
                                "block_size": block_size,
                                "final_status": final_progress.status if final_progress else "unknown",
                                "itinerary": final_itinerary.model_dump(mode="json"),
                            }
                            with open(debug_file, "w") as f:
                                json.dump(debug_data, f, indent=2, default=str)
                            st.info(f"Debug output saved to {debug_file}")

                        st.rerun()

                except Exception as e:
                    st.error(f"Failed to generate itinerary: {e}")

            else:
                # Original single-call generation
                with st.spinner("Generating itinerary..."):
                    try:
                        new_itinerary = st.session_state.agent.generate_itinerary_json(
                            chat_context, st.session_state.session.itinerary, st.session_state.session.language
                        )
                        st.session_state.session.itinerary = new_itinerary
                        # Clear generation state
                        st.session_state.generation_state = GenerationState()

                        # Save debug output if debug mode is enabled
                        if DEBUG_MODE:
                            from datetime import datetime
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            debug_file = DEBUG_DIR / f"itinerary_debug_{timestamp}.json"
                            debug_data = {
                                "timestamp": timestamp,
                                "chat_context": chat_context,
                                "language": st.session_state.session.language,
                                "generation_mode": "single",
                                "itinerary": new_itinerary.model_dump(mode="json"),
                            }
                            with open(debug_file, "w") as f:
                                json.dump(debug_data, f, indent=2, default=str)
                            st.info(f"Debug output saved to {debug_file}")

                        st.success("Itinerary generated!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to generate itinerary: {e}")

    st.markdown("---")

    # Photo loading section
    if itinerary.days:
        days_with_queries = [d for d in itinerary.days if d.image_queries]
        days_with_photos = [d for d in itinerary.days if d.image_paths]

        if days_with_queries and len(days_with_photos) < len(days_with_queries):
            if st.button("📷 Load Photos", key="load_itinerary_photos"):
                if load_photos_for_itinerary(itinerary):
                    st.success("Photos loaded!")
                    st.rerun()
        elif days_with_photos:
            st.caption(f"✓ {len(days_with_photos)} days have photos ({sum(len(d.image_paths) for d in days_with_photos)} total)")

    st.subheader("Day-by-Day Plan")

    if itinerary.days:
        for day in itinerary.days:
            with st.expander(f"Day {day.day_number}: {day.title} - {day.location}", expanded=False):
                # Photo gallery
                if day.image_paths:
                    cols = st.columns(min(len(day.image_paths), 3))
                    for idx, img_path in enumerate(day.image_paths[:3]):
                        with cols[idx]:
                            if Path(img_path).exists():
                                st.image(img_path, use_container_width=True)

                st.markdown(f"**Summary:** {day.summary}")

                if day.activities:
                    st.markdown("**Activities:**")
                    for activity in day.activities:
                        time_str = ""
                        if activity.start_time:
                            time_str = f" ({activity.start_time}"
                            if activity.end_time:
                                time_str += f" - {activity.end_time}"
                            time_str += ")"

                        st.markdown(f"- **{activity.name}**{time_str}")
                        st.markdown(f"  {activity.description}")
                        st.markdown(f"  📍 {activity.location}")
                        if activity.cost_estimate:
                            st.markdown(f"  💰 {activity.cost_estimate}")

                if day.tips:
                    st.markdown("**Tips:**")
                    for tip in day.tips:
                        st.info(f"💡 **{tip.title}:** {tip.content}")

                if day.weather_note:
                    st.markdown(f"🌤️ **Weather:** {day.weather_note}")
    else:
        st.info("No days planned yet. Chat with the AI to plan your trip, then click 'Create Itinerary from Conversation'.")

    if itinerary.general_tips:
        st.markdown("---")
        st.subheader("General Tips")
        for tip in itinerary.general_tips:
            st.info(f"💡 **{tip.title}:** {tip.content}")

    if itinerary.packing_list:
        st.markdown("---")
        st.subheader("Packing List")
        cols = st.columns(3)
        for i, item in enumerate(itinerary.packing_list):
            with cols[i % 3]:
                st.checkbox(item, key=f"pack_{i}")


def render_blog_tips():
    """Render extracted blog tips with blog input UI."""
    st.header("📝 Blog Tips")

    # Blog input section at top
    st.subheader("Add Travel Blog")
    col1, col2 = st.columns([3, 1])
    with col1:
        blog_url = st.text_input("Blog URL", placeholder="https://...", key="blog_url_input")
    with col2:
        use_ai_extraction = st.checkbox("Use AI", value=True, key="use_ai_blog", help="Use AI to extract tips intelligently")

    if st.button("Extract Tips", key="extract_blog"):
        if blog_url:
            scraper = BlogScraper()
            agent = st.session_state.agent

            if use_ai_extraction and agent:
                with st.spinner("Extracting with AI (this may take a moment)..."):
                    content = scraper.scrape_with_ai(blog_url, agent)
            else:
                with st.spinner("Extracting content..."):
                    content = scraper.scrape_blog(blog_url)

            if content:
                st.session_state.blog_content[blog_url] = content
                if blog_url not in st.session_state.session.itinerary.blog_urls:
                    st.session_state.session.itinerary.blog_urls.append(blog_url)
                tip_count = len(content.tips)
                st.success(f"Extracted: {content.title} ({tip_count} tips)")
                st.rerun()
            else:
                st.error("Failed to extract content")
        else:
            st.warning("Please enter a blog URL")

    st.markdown("---")

    # Display extracted blogs
    if st.session_state.blog_content:
        st.subheader(f"Extracted Blogs ({len(st.session_state.blog_content)})")

        urls_to_delete = []
        for url in list(st.session_state.blog_content.keys()):
            content = st.session_state.blog_content[url]
            with st.expander(content.title, expanded=False):
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.markdown(f"**Source:** [{url}]({url})")
                with col2:
                    if st.button("🗑️ Delete", key=f"del_blog_tab_{hash(url)}"):
                        urls_to_delete.append(url)

                st.markdown(f"**Summary:** {content.summary[:300]}...")

                if content.tips:
                    st.markdown("**Tips:**")
                    for tip in content.tips[:5]:
                        st.markdown(f"- {tip}")

                if content.highlights:
                    st.markdown("**Highlights:**")
                    for highlight in content.highlights[:5]:
                        st.markdown(f"- {highlight}")

        # Process deletions after iteration
        for url in urls_to_delete:
            del st.session_state.blog_content[url]
            if url in st.session_state.session.itinerary.blog_urls:
                st.session_state.session.itinerary.blog_urls.remove(url)
            st.success(f"Deleted blog: {url[:50]}...")
            st.rerun()
    else:
        st.info("No blogs added yet. Enter a travel blog URL above to extract tips and highlights.")


def main():
    """Main application entry point."""
    init_session_state()
    render_sidebar()

    tab1, tab2, tab3, tab4 = st.tabs(["💬 Chat", "📋 Itinerary", "📝 Blog Tips", "⚙️ Settings"])

    with tab1:
        render_chat()

    with tab2:
        render_itinerary_builder()

    with tab3:
        render_blog_tips()

    with tab4:
        render_settings()


if __name__ == "__main__":
    main()
