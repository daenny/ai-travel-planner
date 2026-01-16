import json
import os
from pathlib import Path

import keyring
import streamlit as st
from dotenv import load_dotenv

from ai_travel_planner.models import ChatMessage, Itinerary, PlannerSession, SavedBlogContent, TripDestinations
from ai_travel_planner.agents import ClaudeAgent, OpenAIAgent, GeminiAgent
from ai_travel_planner.agents.base import TravelAgent
from ai_travel_planner.services import UnsplashService, BlogScraper, PDFGenerator
from ai_travel_planner.services.pdf_generator import PDFStyle
from ai_travel_planner.services.blog_scraper import BlogContent
from ai_travel_planner.services.destination_detector import DestinationDetector

load_dotenv()

# Keyring service name for storing API keys
KEYRING_SERVICE = "travel-planner"

# Mapping of providers to keyring key names
KEYRING_KEYS = {
    "Claude": "anthropic_api_key",
    "OpenAI": "openai_api_key",
    "Gemini": "google_api_key",
    "Unsplash": "unsplash_access_key",
}


def get_api_key(provider: str) -> str:
    """Get API key from keyring, falling back to environment variable."""
    key_name = KEYRING_KEYS.get(provider, "")

    # Try keyring first
    try:
        key = keyring.get_password(KEYRING_SERVICE, key_name)
        if key:
            return key
    except Exception:
        pass

    # Fall back to environment variables
    env_vars = {
        "Claude": "ANTHROPIC_API_KEY",
        "OpenAI": "OPENAI_API_KEY",
        "Gemini": "GOOGLE_API_KEY",
        "Unsplash": "UNSPLASH_ACCESS_KEY",
    }
    return os.getenv(env_vars.get(provider, ""), "")


def save_api_key(provider: str, api_key: str) -> bool:
    """Save API key to keyring."""
    key_name = KEYRING_KEYS.get(provider, "")
    if not key_name or not api_key:
        return False

    try:
        keyring.set_password(KEYRING_SERVICE, key_name, api_key)
        return True
    except Exception:
        return False


def delete_api_key(provider: str) -> bool:
    """Delete API key from keyring."""
    key_name = KEYRING_KEYS.get(provider, "")
    if not key_name:
        return False

    try:
        keyring.delete_password(KEYRING_SERVICE, key_name)
        return True
    except Exception:
        return False


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

for d in [PLANS_DIR, EXPORTS_DIR, IMAGES_DIR]:
    d.mkdir(exist_ok=True)


def init_session_state():
    """Initialize session state variables."""
    if "session" not in st.session_state:
        st.session_state.session = PlannerSession()
    if "agent" not in st.session_state:
        st.session_state.agent = None
    if "blog_content" not in st.session_state:
        st.session_state.blog_content = {}


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
        "gemini-3-pro-preview",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.5-pro",
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


def render_sidebar():
    """Render the sidebar with configuration options."""
    with st.sidebar:
        st.title(get_app_title(st.session_state.session))
        st.markdown("---")

        st.subheader("AI Provider")
        provider = st.selectbox(
            "Select AI Provider",
            ["Claude", "OpenAI", "Gemini"],
            key="provider_select",
        )

        model = st.selectbox(
            "Select Model",
            PROVIDER_MODELS[provider],
            key=f"model_select_{provider}",
        )

        # Load API key from keyring or environment
        stored_key = get_api_key(provider)
        api_key = st.text_input(
            f"{provider} API Key",
            value=stored_key,
            type="password",
            key=f"api_key_{provider}",
        )

        # Save/delete key buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Key", key=f"save_key_{provider}", use_container_width=True):
                if api_key:
                    if save_api_key(provider, api_key):
                        st.success("Key saved!")
                    else:
                        st.error("Failed to save")
        with col2:
            if st.button("🗑️ Delete", key=f"del_key_{provider}", use_container_width=True):
                if delete_api_key(provider):
                    st.success("Key deleted!")
                    st.rerun()

        current_model = st.session_state.agent.model_id if st.session_state.agent else None
        needs_new_agent = (
            st.session_state.agent is None
            or st.session_state.session.ai_provider != provider
            or current_model != model
        )

        if api_key and needs_new_agent:
            st.session_state.agent = get_agent(provider, api_key, model)
            st.session_state.session.ai_provider = provider
            if st.session_state.agent:
                st.session_state.agent.set_language(st.session_state.session.language)
                st.success(f"Connected to {provider} ({model})")

        st.markdown("---")
        st.subheader("Language")
        current_language = st.session_state.session.language
        language_index = SUPPORTED_LANGUAGES.index(current_language) if current_language in SUPPORTED_LANGUAGES else 0
        language = st.selectbox(
            "Content Language",
            SUPPORTED_LANGUAGES,
            index=language_index,
            key="language_select",
            help="Language for AI-generated content (descriptions, tips, activities)"
        )
        if language != st.session_state.session.language:
            st.session_state.session.language = language
            if st.session_state.agent:
                st.session_state.agent.set_language(language)

        st.markdown("---")
        st.subheader("Unsplash Images")
        stored_unsplash = get_api_key("Unsplash")
        st.text_input(
            "Unsplash Access Key",
            value=stored_unsplash,
            type="password",
            key="unsplash_key",
        )
        if st.button("💾 Save Unsplash Key", key="save_unsplash"):
            unsplash_val = st.session_state.get("unsplash_key", "")
            if unsplash_val:
                if save_api_key("Unsplash", unsplash_val):
                    st.success("Unsplash key saved!")
                else:
                    st.error("Failed to save")

        st.markdown("---")
        st.subheader("Travel Blogs")
        blog_url = st.text_input("Add blog URL", placeholder="https://...", key="blog_url_input")
        use_ai_extraction = st.checkbox("Use AI to extract tips", value=True, key="use_ai_blog")

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
                else:
                    st.error("Failed to extract content")

        if st.session_state.blog_content:
            st.markdown("**Added blogs:**")
            urls_to_delete = []
            for url in list(st.session_state.blog_content.keys()):
                content = st.session_state.blog_content[url]
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"- {content.title[:25]}... ({len(content.tips)} tips)")
                with col2:
                    if st.button("🗑️", key=f"del_blog_sidebar_{hash(url)}", help="Delete blog"):
                        urls_to_delete.append(url)

            # Process deletions after iteration
            for url in urls_to_delete:
                del st.session_state.blog_content[url]
                if url in st.session_state.session.itinerary.blog_urls:
                    st.session_state.session.itinerary.blog_urls.remove(url)
                st.rerun()

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
                    st.success(f"Loaded: {uploaded_file.name} ({len(st.session_state.blog_content)} blogs)")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to load session: {e}")

        # Save session via download button
        st.markdown("**Save current session:**")
        save_name = st.text_input("Filename", placeholder="my_trip", key="save_name")
        if save_name:
            # Sync blog content before saving
            sync_blog_content_to_session()
            session_json = st.session_state.session.model_dump_json(indent=2)
            filename = f"session_{save_name}.json" if not save_name.endswith(".json") else save_name
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
                    unsplash_api_key = st.session_state.get("unsplash_key", "")
                    if unsplash_api_key:
                        unsplash = UnsplashService(unsplash_api_key, IMAGES_DIR)
                        for day in st.session_state.session.itinerary.days:
                            if not day.image_path:
                                img_path = unsplash.get_photo_for_location(day.location)
                                if img_path:
                                    day.image_path = str(img_path)

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

    # Chat input at the top
    chat_placeholder = get_chat_placeholder(st.session_state.session)
    prompt = st.chat_input(chat_placeholder)

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
        if st.button("Create Itinerary from Conversation", key="gen_itinerary"):
            with st.spinner("Generating itinerary..."):
                try:
                    chat_context = "\n".join(
                        f"{msg.role}: {msg.content}"
                        for msg in st.session_state.session.chat_history
                    )
                    new_itinerary = st.session_state.agent.generate_itinerary_json(
                        chat_context, st.session_state.session.itinerary, st.session_state.session.language
                    )
                    st.session_state.session.itinerary = new_itinerary
                    st.success("Itinerary generated!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to generate itinerary: {e}")

    st.markdown("---")
    st.subheader("Day-by-Day Plan")

    if itinerary.days:
        for day in itinerary.days:
            with st.expander(f"Day {day.day_number}: {day.title} - {day.location}", expanded=False):
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
    """Render extracted blog tips."""
    if st.session_state.blog_content:
        st.header("📝 Tips from Blogs")

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
        st.info("No blogs added yet. Add blog URLs in the sidebar to extract travel tips.")


def main():
    """Main application entry point."""
    init_session_state()
    render_sidebar()

    tab1, tab2, tab3 = st.tabs(["💬 Chat", "📋 Itinerary", "📝 Blog Tips"])

    with tab1:
        render_chat()

    with tab2:
        render_itinerary_builder()

    with tab3:
        render_blog_tips()


if __name__ == "__main__":
    main()
