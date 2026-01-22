"""Itinerary tab renderer for the Travel Planner UI."""

from pathlib import Path

import streamlit as st

from ai_travel_planner.models import GenerationState
from ai_travel_planner.services import (
    generate_itinerary_iteratively,
    resume_itinerary_generation,
)
from ai_travel_planner.services.itinerary_updater import apply_diff, validate_diff, DiffParseError
from ai_travel_planner.ui.diff_preview import render_diff_preview
from ai_travel_planner.ui.helpers import render_settings_prompt, save_debug_output, load_photos_for_itinerary


def render_itinerary_builder(local_mode: bool, debug_mode: bool):
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

    # Generate Itinerary section
    st.subheader("Generate Itinerary from Chat")

    if not st.session_state.agent:
        render_settings_prompt("Connect to an AI provider to generate itineraries.")
    else:

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
                        save_debug_output(
                            final_itinerary, chat_context,
                            mode="iterative" + ("_resume" if is_resume else ""),
                            debug_mode=debug_mode,
                            block_size=block_size,
                            final_status=final_progress.status if final_progress else "unknown",
                        )
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
                        st.session_state.generation_state = GenerationState()
                        save_debug_output(new_itinerary, chat_context, mode="single", debug_mode=debug_mode)
                        st.success("Itinerary generated!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to generate itinerary: {e}")

    st.markdown("---")

    # Update Itinerary section - only show when itinerary has days
    if itinerary.days:
        st.subheader("Update Itinerary")

        if not st.session_state.agent:
            render_settings_prompt("Connect to an AI provider to update your itinerary.")
        elif st.session_state.pending_diff is not None:
            # Show the diff preview
            render_diff_preview(itinerary, st.session_state.pending_diff)

            # Show accept/reject buttons
            col_accept, col_reject = st.columns(2)
            with col_accept:
                if st.button("Accept Changes", type="primary", use_container_width=True, key="accept_diff"):
                    # Validate and apply the diff
                    errors = validate_diff(itinerary, st.session_state.pending_diff)
                    if errors:
                        for error in errors:
                            st.error(error)
                    else:
                        updated_itinerary = apply_diff(itinerary, st.session_state.pending_diff)
                        st.session_state.session.itinerary = updated_itinerary
                        st.session_state.pending_diff = None
                        st.success("Changes applied!")
                        st.rerun()
            with col_reject:
                if st.button("Reject Changes", type="secondary", use_container_width=True, key="reject_diff"):
                    st.session_state.pending_diff = None
                    st.rerun()
        else:
            # Show update request form
            with st.form("update_request_form", clear_on_submit=True):
                update_request = st.text_area(
                    "What would you like to change?",
                    placeholder="e.g., Add a beach day after day 2, swap days 3 and 4, remove the museum visit from day 1",
                    height=80,
                )
                submitted = st.form_submit_button("Generate Changes", type="primary")

                if submitted and update_request.strip():
                    with st.spinner("Generating changes..."):
                        try:
                            diff = st.session_state.agent.generate_itinerary_update(
                                current_itinerary=itinerary,
                                update_request=update_request.strip(),
                                language=st.session_state.session.language,
                            )
                            st.session_state.pending_diff = diff
                            st.rerun()
                        except DiffParseError as e:
                            # User-friendly error from diff parsing
                            st.error(f"⚠️ {e.message}")
                            st.caption("Try rephrasing your request or simplifying the changes.")
                        except Exception as e:
                            # Generic API or network error
                            st.error(f"❌ Failed to generate changes: {e}")
                            st.caption("Check your API key and network connection.")

    st.markdown("---")

    # Photo loading section
    if itinerary.days:
        days_with_queries = [d for d in itinerary.days if d.image_queries]
        days_with_photos = [d for d in itinerary.days if d.image_paths]

        if days_with_queries and len(days_with_photos) < len(days_with_queries):
            if st.button("📷 Load Photos", key="load_itinerary_photos"):
                if load_photos_for_itinerary(itinerary, local_mode):
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
