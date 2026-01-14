import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import keyring
import streamlit as st
from dotenv import load_dotenv

from src.models import ChatMessage, Itinerary, PlannerSession
from src.agents import ClaudeAgent, OpenAIAgent, GeminiAgent
from src.agents.base import TravelAgent
from src.services import UnsplashService, BlogScraper, PDFGenerator
from src.services.pdf_generator import PDFStyle
from src.storage import JSONStore

load_dotenv()

# Keyring service name for storing API keys
KEYRING_SERVICE = "borneo-travel-planner"

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

st.set_page_config(
    page_title="Borneo Travel Planner",
    page_icon="🌴",
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
        "claude-sonnet-4-20250514",
        "claude-opus-4-20250514",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
    ],
    "OpenAI": [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "o1",
        "o1-mini",
    ],
    "Gemini": [
        "gemini-3-pro-preview",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
    ],
}


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


def render_sidebar():
    """Render the sidebar with configuration options."""
    with st.sidebar:
        st.title("🌴 Borneo Planner")
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
                st.success(f"Connected to {provider} ({model})")

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
            for url in st.session_state.blog_content:
                content = st.session_state.blog_content[url]
                st.markdown(f"- {content.title[:30]}... ({len(content.tips)} tips)")

        st.markdown("---")
        st.subheader("Save/Load Plans")

        store = JSONStore(PLANS_DIR)
        sessions = store.list_sessions()

        if sessions:
            selected_session = st.selectbox("Load session", [""] + sessions, key="load_session")
            if selected_session and st.button("Load", key="load_btn"):
                loaded = store.load_session(selected_session)
                if loaded:
                    st.session_state.session = loaded
                    st.success(f"Loaded: {selected_session}")
                    st.rerun()

        save_name = st.text_input("Save as", placeholder="my_borneo_trip", key="save_name")
        if st.button("Save Session", key="save_btn"):
            if save_name:
                store.save_session(st.session_state.session, save_name)
                st.success(f"Saved: {save_name}")

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

    for msg in st.session_state.session.chat_history:
        with st.chat_message(msg.role):
            st.markdown(msg.content)

    if prompt := st.chat_input("Ask about your Borneo trip..."):
        st.session_state.session.chat_history.append(
            ChatMessage(role="user", content=prompt)
        )
        with st.chat_message("user"):
            st.markdown(prompt)

        if st.session_state.agent:
            with st.chat_message("assistant"):
                response_placeholder = st.empty()
                full_response = ""

                try:
                    history = st.session_state.session.chat_history[:-1]

                    for chunk in st.session_state.agent.chat(prompt, history):
                        full_response += chunk
                        response_placeholder.markdown(full_response + "▌")

                    response_placeholder.markdown(full_response)
                    st.session_state.session.chat_history.append(
                        ChatMessage(role="assistant", content=full_response)
                    )
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.warning("Please configure an AI provider in the sidebar.")


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
                        chat_context, st.session_state.session.itinerary
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

        for url, content in st.session_state.blog_content.items():
            with st.expander(content.title, expanded=False):
                st.markdown(f"**Source:** [{url}]({url})")
                st.markdown(f"**Summary:** {content.summary[:300]}...")

                if content.tips:
                    st.markdown("**Tips:**")
                    for tip in content.tips[:5]:
                        st.markdown(f"- {tip}")

                if content.highlights:
                    st.markdown("**Highlights:**")
                    for highlight in content.highlights[:5]:
                        st.markdown(f"- {highlight}")


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
