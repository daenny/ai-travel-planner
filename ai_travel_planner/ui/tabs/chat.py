"""Chat tab renderer for the Travel Planner UI."""

import streamlit as st

from ai_travel_planner.models import ChatMessage
from ai_travel_planner.ui.helpers import (
    get_chat_placeholder,
    render_settings_prompt,
    maybe_update_destination,
    get_blog_context,
)


def render_chat():
    """Render the chat interface."""
    st.header("💬 Plan Your Trip")

    # Check if AI provider is configured
    has_agent = st.session_state.agent is not None

    if not has_agent:
        render_settings_prompt("No AI provider configured.")

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
