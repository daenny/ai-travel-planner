"""UI components for displaying and managing itinerary diffs."""

import streamlit as st

from ai_travel_planner.models.itinerary import (
    Itinerary,
    ItineraryDiff,
    DayDiff,
    DayDiffType,
    ActivityDiff,
    ActivityDiffType,
)
from ai_travel_planner.services.itinerary_updater import preview_diff


def render_diff_preview(itinerary: Itinerary, diff: ItineraryDiff) -> None:
    """Render a visual preview of the proposed changes.

    Args:
        itinerary: The current itinerary
        diff: The proposed changes
    """
    st.subheader("Proposed Changes")
    st.markdown(f"**Summary:** {diff.summary}")

    if not diff.has_changes:
        st.info("No changes detected.")
        return

    # Generate detailed preview
    preview = preview_diff(itinerary, diff)

    # Group changes by type for cleaner display
    metadata_changes = []
    day_changes = []
    activity_changes = []

    for change in preview["changes"]:
        change_type = change["type"]
        if change_type == "metadata":
            metadata_changes.append(change)
        elif change_type.startswith("day_"):
            day_changes.append(change)
        elif change_type.startswith("activity_"):
            activity_changes.append(change)

    # Display metadata changes
    if metadata_changes:
        st.markdown("**Trip Details:**")
        for change in metadata_changes:
            _render_field_change(change)

    # Display day-level changes
    if day_changes:
        st.markdown("**Day Changes:**")
        for change in day_changes:
            _render_day_change(change)

    # Display activity changes
    if activity_changes:
        st.markdown("**Activity Changes:**")
        for change in activity_changes:
            _render_activity_change(change)


def _render_field_change(change: dict) -> None:
    """Render a field change with color-coded old/new values."""
    field = change.get("field", "")
    old_val = change.get("old_value", "")
    new_val = change.get("new_value", "")

    st.markdown(
        f"- **{field}**: "
        f":red[~~{old_val}~~] :arrow_right: :green[{new_val}]"
    )


def _render_day_change(change: dict) -> None:
    """Render a day-level change."""
    change_type = change["type"]
    description = change.get("description", "")

    if change_type == "day_add":
        st.markdown(f":green[+ {description}]")
    elif change_type == "day_remove":
        st.markdown(f":red[- {description}]")
    elif change_type == "day_swap":
        st.markdown(f":blue[↔ {description}]")
    elif change_type == "day_modify":
        field = change.get("field", "")
        old_val = change.get("old_value", "")
        new_val = change.get("new_value", "")
        day_num = change.get("day_number", "?")
        st.markdown(
            f"- Day {day_num} **{field}**: "
            f":red[~~{old_val}~~] :arrow_right: :green[{new_val}]"
        )


def _render_activity_change(change: dict) -> None:
    """Render an activity-level change."""
    change_type = change["type"]
    day_num = change.get("day_number", "?")

    if change_type == "activity_add":
        description = change.get("description", "Add activity")
        st.markdown(f":green[+ {description}]")
    elif change_type == "activity_remove":
        description = change.get("description", "Remove activity")
        st.markdown(f":red[- {description}]")
    elif change_type == "activity_modify":
        description = change.get("description", "Modify activity")
        st.markdown(f":orange[~ {description}]")


def render_diff_actions(on_accept: callable, on_reject: callable) -> None:
    """Render Accept/Reject buttons for pending changes.

    Args:
        on_accept: Callback when changes are accepted
        on_reject: Callback when changes are rejected
    """
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Accept Changes", type="primary", use_container_width=True):
            on_accept()
    with col2:
        if st.button("Reject Changes", type="secondary", use_container_width=True):
            on_reject()


def render_update_request_form(
    on_submit: callable,
    disabled: bool = False,
) -> None:
    """Render the update request input form.

    Args:
        on_submit: Callback when form is submitted with the request text
        disabled: Whether the form should be disabled
    """
    with st.form("update_request_form", clear_on_submit=True):
        update_request = st.text_area(
            "What would you like to change?",
            placeholder="e.g., Add a beach day after day 2, or swap days 3 and 4",
            height=100,
            disabled=disabled,
        )
        submitted = st.form_submit_button(
            "Generate Changes",
            type="primary",
            disabled=disabled,
        )
        if submitted and update_request.strip():
            on_submit(update_request.strip())
