"""Service for applying diffs to itineraries."""

from copy import deepcopy
from typing import Any


class DiffParseError(Exception):
    """Error raised when parsing an AI-generated diff fails.

    Attributes:
        message: Human-readable error message
        raw_response: The raw response that failed to parse (if available)
        cause: The underlying exception that caused the failure
    """

    def __init__(
        self,
        message: str,
        raw_response: str | None = None,
        cause: Exception | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.raw_response = raw_response
        self.cause = cause

    def __str__(self) -> str:
        return self.message


from ai_travel_planner.models.itinerary import (
    Itinerary,
    DayPlan,
    Activity,
    ItineraryDiff,
    DayDiff,
    DayDiffType,
    ActivityDiff,
    ActivityDiffType,
    FieldChange,
)


def apply_diff(itinerary: Itinerary, diff: ItineraryDiff) -> Itinerary:
    """Apply a diff to an itinerary and return the updated itinerary.

    This function does not mutate the original itinerary.

    Args:
        itinerary: The original itinerary to update
        diff: The diff containing changes to apply

    Returns:
        A new Itinerary with the changes applied
    """
    # Deep copy to avoid mutating the original
    result = deepcopy(itinerary)

    # Apply metadata changes first
    for change in diff.metadata_changes:
        _apply_field_change(result, change)

    # Apply day diffs
    for day_diff in diff.day_diffs:
        _apply_day_diff(result, day_diff)

    return result


def _apply_field_change(obj: Any, change: FieldChange) -> None:
    """Apply a field change to an object."""
    if hasattr(obj, change.field):
        setattr(obj, change.field, change.new_value)


def _apply_day_diff(itinerary: Itinerary, day_diff: DayDiff) -> None:
    """Apply a day-level diff to the itinerary."""
    if day_diff.operation == DayDiffType.ADD:
        _add_day(itinerary, day_diff)
    elif day_diff.operation == DayDiffType.REMOVE:
        _remove_day(itinerary, day_diff)
    elif day_diff.operation == DayDiffType.MODIFY:
        _modify_day(itinerary, day_diff)
    elif day_diff.operation == DayDiffType.SWAP:
        _swap_days(itinerary, day_diff)


def _add_day(itinerary: Itinerary, day_diff: DayDiff) -> None:
    """Add a new day to the itinerary."""
    if day_diff.day is None:
        return

    position = day_diff.position or len(itinerary.days) + 1
    new_day = deepcopy(day_diff.day)

    # Insert at the correct position (position is 1-indexed)
    insert_index = position - 1
    if insert_index >= len(itinerary.days):
        itinerary.days.append(new_day)
    else:
        itinerary.days.insert(insert_index, new_day)

    # Renumber all days
    _renumber_days(itinerary)


def _remove_day(itinerary: Itinerary, day_diff: DayDiff) -> None:
    """Remove a day from the itinerary."""
    day_number = day_diff.day_number
    if day_number is None:
        return

    # Find and remove the day
    day_index = _find_day_index(itinerary, day_number)
    if day_index is not None:
        itinerary.days.pop(day_index)
        # Renumber all days
        _renumber_days(itinerary)


def _modify_day(itinerary: Itinerary, day_diff: DayDiff) -> None:
    """Modify an existing day in the itinerary."""
    day_number = day_diff.day_number
    if day_number is None:
        return

    day_index = _find_day_index(itinerary, day_number)
    if day_index is None:
        return

    day = itinerary.days[day_index]

    # Apply field changes to the day
    for change in day_diff.field_changes:
        _apply_field_change(day, change)

    # Apply activity diffs
    for activity_diff in day_diff.activity_diffs:
        _apply_activity_diff(day, activity_diff)


def _swap_days(itinerary: Itinerary, day_diff: DayDiff) -> None:
    """Swap two days in the itinerary."""
    day_a_num = day_diff.day_number
    day_b_num = day_diff.swap_with_day

    if day_a_num is None or day_b_num is None:
        return

    day_a_index = _find_day_index(itinerary, day_a_num)
    day_b_index = _find_day_index(itinerary, day_b_num)

    if day_a_index is None or day_b_index is None:
        return

    # Swap the days
    itinerary.days[day_a_index], itinerary.days[day_b_index] = (
        itinerary.days[day_b_index],
        itinerary.days[day_a_index],
    )

    # Renumber to maintain correct day_number sequence
    _renumber_days(itinerary)


def _apply_activity_diff(day: DayPlan, activity_diff: ActivityDiff) -> None:
    """Apply an activity-level diff to a day."""
    if activity_diff.operation == ActivityDiffType.ADD:
        _add_activity(day, activity_diff)
    elif activity_diff.operation == ActivityDiffType.REMOVE:
        _remove_activity(day, activity_diff)
    elif activity_diff.operation == ActivityDiffType.MODIFY:
        _modify_activity(day, activity_diff)


def _add_activity(day: DayPlan, activity_diff: ActivityDiff) -> None:
    """Add a new activity to a day."""
    if activity_diff.activity is None:
        return

    position = activity_diff.position
    new_activity = deepcopy(activity_diff.activity)

    if position is None or position >= len(day.activities):
        day.activities.append(new_activity)
    else:
        day.activities.insert(position, new_activity)


def _remove_activity(day: DayPlan, activity_diff: ActivityDiff) -> None:
    """Remove an activity from a day."""
    index = activity_diff.activity_index
    if index is None or index >= len(day.activities):
        return

    day.activities.pop(index)


def _modify_activity(day: DayPlan, activity_diff: ActivityDiff) -> None:
    """Modify an existing activity."""
    index = activity_diff.activity_index
    if index is None or index >= len(day.activities):
        return

    activity = day.activities[index]

    # Apply field changes
    for change in activity_diff.field_changes:
        _apply_field_change(activity, change)


def _find_day_index(itinerary: Itinerary, day_number: int) -> int | None:
    """Find the index of a day by its day_number."""
    for i, day in enumerate(itinerary.days):
        if day.day_number == day_number:
            return i
    return None


def _renumber_days(itinerary: Itinerary) -> None:
    """Renumber all days sequentially starting from 1."""
    for i, day in enumerate(itinerary.days):
        day.day_number = i + 1


def validate_diff(itinerary: Itinerary, diff: ItineraryDiff) -> list[str]:
    """Validate that a diff can be applied to an itinerary.

    Args:
        itinerary: The itinerary to validate against
        diff: The diff to validate

    Returns:
        List of error messages. Empty list means the diff is valid.
    """
    errors = []

    # Get set of valid day numbers
    valid_day_numbers = {day.day_number for day in itinerary.days}

    for day_diff in diff.day_diffs:
        # For operations that reference existing days
        if day_diff.operation in (DayDiffType.MODIFY, DayDiffType.REMOVE, DayDiffType.SWAP):
            if day_diff.day_number is not None and day_diff.day_number not in valid_day_numbers:
                errors.append(f"Day {day_diff.day_number} does not exist in the itinerary")

            # For swap, also check the other day
            if day_diff.operation == DayDiffType.SWAP:
                if day_diff.swap_with_day is not None and day_diff.swap_with_day not in valid_day_numbers:
                    errors.append(f"Day {day_diff.swap_with_day} does not exist in the itinerary")

        # Validate activity diffs
        if day_diff.day_number is not None and day_diff.day_number in valid_day_numbers:
            day_index = _find_day_index(itinerary, day_diff.day_number)
            if day_index is not None:
                day = itinerary.days[day_index]
                for activity_diff in day_diff.activity_diffs:
                    if activity_diff.operation in (ActivityDiffType.REMOVE, ActivityDiffType.MODIFY):
                        if activity_diff.activity_index is not None:
                            if activity_diff.activity_index >= len(day.activities):
                                errors.append(
                                    f"Activity index {activity_diff.activity_index} does not exist in day {day_diff.day_number}"
                                )

    return errors


def preview_diff(itinerary: Itinerary, diff: ItineraryDiff) -> dict:
    """Generate a preview of what changes will be made.

    Args:
        itinerary: The itinerary that will be modified
        diff: The diff to preview

    Returns:
        Dictionary containing summary and list of changes
    """
    changes = []

    # Describe metadata changes
    for change in diff.metadata_changes:
        changes.append({
            "type": "metadata",
            "field": change.field,
            "old_value": change.old_value,
            "new_value": change.new_value,
            "description": f"Change {change.field} from '{change.old_value}' to '{change.new_value}'",
        })

    # Describe day changes
    for day_diff in diff.day_diffs:
        if day_diff.operation == DayDiffType.ADD:
            day_title = day_diff.day.title if day_diff.day else "New Day"
            changes.append({
                "type": "day_add",
                "position": day_diff.position,
                "description": f"Add new day '{day_title}' at position {day_diff.position}",
            })

        elif day_diff.operation == DayDiffType.REMOVE:
            day_index = _find_day_index(itinerary, day_diff.day_number)
            day_title = itinerary.days[day_index].title if day_index is not None else f"Day {day_diff.day_number}"
            changes.append({
                "type": "day_remove",
                "day_number": day_diff.day_number,
                "description": f"Remove day {day_diff.day_number} ('{day_title}')",
            })

        elif day_diff.operation == DayDiffType.SWAP:
            changes.append({
                "type": "day_swap",
                "day_a": day_diff.day_number,
                "day_b": day_diff.swap_with_day,
                "description": f"Swap day {day_diff.day_number} with day {day_diff.swap_with_day}",
            })

        elif day_diff.operation == DayDiffType.MODIFY:
            # Field changes
            for change in day_diff.field_changes:
                changes.append({
                    "type": "day_modify",
                    "day_number": day_diff.day_number,
                    "field": change.field,
                    "old_value": change.old_value,
                    "new_value": change.new_value,
                    "description": f"Day {day_diff.day_number}: Change {change.field} from '{change.old_value}' to '{change.new_value}'",
                })

            # Activity changes
            for activity_diff in day_diff.activity_diffs:
                if activity_diff.operation == ActivityDiffType.ADD:
                    activity_name = activity_diff.activity.name if activity_diff.activity else "New Activity"
                    changes.append({
                        "type": "activity_add",
                        "day_number": day_diff.day_number,
                        "position": activity_diff.position,
                        "description": f"Day {day_diff.day_number}: Add activity '{activity_name}' at position {activity_diff.position}",
                    })

                elif activity_diff.operation == ActivityDiffType.REMOVE:
                    changes.append({
                        "type": "activity_remove",
                        "day_number": day_diff.day_number,
                        "activity_index": activity_diff.activity_index,
                        "description": f"Day {day_diff.day_number}: Remove activity at index {activity_diff.activity_index}",
                    })

                elif activity_diff.operation == ActivityDiffType.MODIFY:
                    for change in activity_diff.field_changes:
                        changes.append({
                            "type": "activity_modify",
                            "day_number": day_diff.day_number,
                            "activity_index": activity_diff.activity_index,
                            "field": change.field,
                            "description": f"Day {day_diff.day_number}, Activity {activity_diff.activity_index}: Change {change.field}",
                        })

    return {
        "summary": diff.summary,
        "changes": changes,
        "change_count": len(changes),
    }
