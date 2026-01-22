"""Tests for itinerary diff models.

These models support diff-based itinerary updates to minimize token usage
and provide visual change tracking.
"""

from enum import Enum
from typing import Any
import pytest
from pydantic import ValidationError


class TestFieldChange:
    """Tests for FieldChange model - generic field-level changes."""

    def test_field_change_creation_with_strings(self):
        """Test creating a FieldChange with string values."""
        from ai_travel_planner.models.itinerary import FieldChange

        change = FieldChange(
            field="title",
            old_value="Old Title",
            new_value="New Title"
        )

        assert change.field == "title"
        assert change.old_value == "Old Title"
        assert change.new_value == "New Title"

    def test_field_change_creation_with_none_old_value(self):
        """Test creating a FieldChange where old_value is None (new field)."""
        from ai_travel_planner.models.itinerary import FieldChange

        change = FieldChange(
            field="budget_estimate",
            old_value=None,
            new_value="$5000"
        )

        assert change.field == "budget_estimate"
        assert change.old_value is None
        assert change.new_value == "$5000"

    def test_field_change_creation_with_none_new_value(self):
        """Test creating a FieldChange where new_value is None (field removal)."""
        from ai_travel_planner.models.itinerary import FieldChange

        change = FieldChange(
            field="weather_note",
            old_value="Sunny and warm",
            new_value=None
        )

        assert change.field == "weather_note"
        assert change.old_value == "Sunny and warm"
        assert change.new_value is None

    def test_field_change_creation_with_integers(self):
        """Test creating a FieldChange with integer values."""
        from ai_travel_planner.models.itinerary import FieldChange

        change = FieldChange(
            field="travelers",
            old_value=4,
            new_value=6
        )

        assert change.field == "travelers"
        assert change.old_value == 4
        assert change.new_value == 6

    def test_field_change_creation_with_lists(self):
        """Test creating a FieldChange with list values."""
        from ai_travel_planner.models.itinerary import FieldChange

        change = FieldChange(
            field="packing_list",
            old_value=["sunscreen", "hat"],
            new_value=["sunscreen", "hat", "umbrella"]
        )

        assert change.field == "packing_list"
        assert change.old_value == ["sunscreen", "hat"]
        assert change.new_value == ["sunscreen", "hat", "umbrella"]

    def test_field_change_requires_field_name(self):
        """Test that FieldChange requires a field name."""
        from ai_travel_planner.models.itinerary import FieldChange

        with pytest.raises(ValidationError):
            FieldChange(
                old_value="old",
                new_value="new"
            )

    def test_field_change_field_cannot_be_empty(self):
        """Test that field name cannot be empty string."""
        from ai_travel_planner.models.itinerary import FieldChange

        with pytest.raises(ValidationError):
            FieldChange(
                field="",
                old_value="old",
                new_value="new"
            )

    def test_field_change_serialization(self):
        """Test that FieldChange serializes correctly to dict."""
        from ai_travel_planner.models.itinerary import FieldChange

        change = FieldChange(
            field="title",
            old_value="Old",
            new_value="New"
        )

        data = change.model_dump()
        assert data["field"] == "title"
        assert data["old_value"] == "Old"
        assert data["new_value"] == "New"

    def test_field_change_from_dict(self):
        """Test creating FieldChange from dictionary."""
        from ai_travel_planner.models.itinerary import FieldChange

        data = {
            "field": "description",
            "old_value": "Old description",
            "new_value": "New description"
        }

        change = FieldChange(**data)
        assert change.field == "description"
        assert change.old_value == "Old description"
        assert change.new_value == "New description"

    def test_field_change_is_addition_property(self):
        """Test is_addition property returns True when old_value is None."""
        from ai_travel_planner.models.itinerary import FieldChange

        change = FieldChange(
            field="budget",
            old_value=None,
            new_value="$1000"
        )

        assert change.is_addition is True

    def test_field_change_is_removal_property(self):
        """Test is_removal property returns True when new_value is None."""
        from ai_travel_planner.models.itinerary import FieldChange

        change = FieldChange(
            field="budget",
            old_value="$1000",
            new_value=None
        )

        assert change.is_removal is True

    def test_field_change_is_modification_property(self):
        """Test is_modification property returns True when both values exist."""
        from ai_travel_planner.models.itinerary import FieldChange

        change = FieldChange(
            field="title",
            old_value="Old Title",
            new_value="New Title"
        )

        assert change.is_modification is True
        assert change.is_addition is False
        assert change.is_removal is False


class TestActivityDiff:
    """Tests for ActivityDiff model - activity-level changes within a day."""

    def test_activity_diff_add_operation(self):
        """Test creating an ActivityDiff for adding an activity."""
        from ai_travel_planner.models.itinerary import ActivityDiff, Activity, ActivityDiffType

        new_activity = Activity(
            name="Beach Visit",
            description="Relaxing day at the beach",
            location="Kuta Beach"
        )

        diff = ActivityDiff(
            operation=ActivityDiffType.ADD,
            activity=new_activity,
            position=2
        )

        assert diff.operation == ActivityDiffType.ADD
        assert diff.activity.name == "Beach Visit"
        assert diff.position == 2
        assert diff.activity_index is None

    def test_activity_diff_remove_operation(self):
        """Test creating an ActivityDiff for removing an activity."""
        from ai_travel_planner.models.itinerary import ActivityDiff, ActivityDiffType

        diff = ActivityDiff(
            operation=ActivityDiffType.REMOVE,
            activity_index=1
        )

        assert diff.operation == ActivityDiffType.REMOVE
        assert diff.activity_index == 1
        assert diff.activity is None

    def test_activity_diff_modify_operation(self):
        """Test creating an ActivityDiff for modifying an activity."""
        from ai_travel_planner.models.itinerary import ActivityDiff, ActivityDiffType, FieldChange

        field_changes = [
            FieldChange(field="name", old_value="Temple Visit", new_value="Temple Tour"),
            FieldChange(field="start_time", old_value="09:00", new_value="10:00")
        ]

        diff = ActivityDiff(
            operation=ActivityDiffType.MODIFY,
            activity_index=0,
            field_changes=field_changes
        )

        assert diff.operation == ActivityDiffType.MODIFY
        assert diff.activity_index == 0
        assert len(diff.field_changes) == 2
        assert diff.field_changes[0].field == "name"

    def test_activity_diff_type_enum_values(self):
        """Test that ActivityDiffType has expected enum values."""
        from ai_travel_planner.models.itinerary import ActivityDiffType

        assert ActivityDiffType.ADD.value == "add"
        assert ActivityDiffType.REMOVE.value == "remove"
        assert ActivityDiffType.MODIFY.value == "modify"

    def test_activity_diff_add_requires_activity(self):
        """Test that ADD operation should have an activity."""
        from ai_travel_planner.models.itinerary import ActivityDiff, ActivityDiffType, Activity

        # Should work with activity
        activity = Activity(name="Test", description="Test", location="Test")
        diff = ActivityDiff(operation=ActivityDiffType.ADD, activity=activity)
        assert diff.activity is not None

    def test_activity_diff_remove_requires_activity_index(self):
        """Test that REMOVE operation should have an activity_index."""
        from ai_travel_planner.models.itinerary import ActivityDiff, ActivityDiffType

        # Should work with activity_index
        diff = ActivityDiff(operation=ActivityDiffType.REMOVE, activity_index=0)
        assert diff.activity_index == 0

    def test_activity_diff_modify_requires_activity_index(self):
        """Test that MODIFY operation should have an activity_index."""
        from ai_travel_planner.models.itinerary import ActivityDiff, ActivityDiffType, FieldChange

        # Should work with activity_index and field_changes
        diff = ActivityDiff(
            operation=ActivityDiffType.MODIFY,
            activity_index=0,
            field_changes=[FieldChange(field="name", old_value="A", new_value="B")]
        )
        assert diff.activity_index == 0
        assert len(diff.field_changes) == 1

    def test_activity_diff_serialization(self):
        """Test that ActivityDiff serializes correctly."""
        from ai_travel_planner.models.itinerary import ActivityDiff, Activity, ActivityDiffType

        activity = Activity(
            name="Hiking",
            description="Mountain hike",
            location="Mount Kinabalu"
        )

        diff = ActivityDiff(
            operation=ActivityDiffType.ADD,
            activity=activity,
            position=0
        )

        data = diff.model_dump()
        assert data["operation"] == "add"
        assert data["activity"]["name"] == "Hiking"
        assert data["position"] == 0

    def test_activity_diff_from_dict(self):
        """Test creating ActivityDiff from dictionary."""
        from ai_travel_planner.models.itinerary import ActivityDiff

        data = {
            "operation": "remove",
            "activity_index": 2
        }

        diff = ActivityDiff(**data)
        assert diff.operation.value == "remove"
        assert diff.activity_index == 2

    def test_activity_diff_default_values(self):
        """Test ActivityDiff default values."""
        from ai_travel_planner.models.itinerary import ActivityDiff, ActivityDiffType

        diff = ActivityDiff(operation=ActivityDiffType.REMOVE, activity_index=0)

        assert diff.activity is None
        assert diff.position is None
        assert diff.field_changes == []


class TestDayDiff:
    """Tests for DayDiff model - day-level changes in an itinerary."""

    def test_day_diff_add_day(self):
        """Test creating a DayDiff for adding a new day."""
        from ai_travel_planner.models.itinerary import DayDiff, DayDiffType, DayPlan, Activity

        new_day = DayPlan(
            day_number=5,
            title="Beach Day",
            location="Kuta Beach",
            summary="Relaxing beach day",
            activities=[
                Activity(name="Swimming", description="Ocean swim", location="Kuta Beach")
            ]
        )

        diff = DayDiff(
            operation=DayDiffType.ADD,
            day=new_day,
            position=4  # Insert at position 4 (0-indexed)
        )

        assert diff.operation == DayDiffType.ADD
        assert diff.day.title == "Beach Day"
        assert diff.position == 4
        assert diff.day_number is None

    def test_day_diff_remove_day(self):
        """Test creating a DayDiff for removing a day."""
        from ai_travel_planner.models.itinerary import DayDiff, DayDiffType

        diff = DayDiff(
            operation=DayDiffType.REMOVE,
            day_number=3
        )

        assert diff.operation == DayDiffType.REMOVE
        assert diff.day_number == 3
        assert diff.day is None

    def test_day_diff_modify_day_fields(self):
        """Test creating a DayDiff for modifying day fields."""
        from ai_travel_planner.models.itinerary import DayDiff, DayDiffType, FieldChange

        diff = DayDiff(
            operation=DayDiffType.MODIFY,
            day_number=2,
            field_changes=[
                FieldChange(field="title", old_value="Temple Day", new_value="Culture Day"),
                FieldChange(field="summary", old_value="Old summary", new_value="New summary")
            ]
        )

        assert diff.operation == DayDiffType.MODIFY
        assert diff.day_number == 2
        assert len(diff.field_changes) == 2
        assert diff.field_changes[0].field == "title"

    def test_day_diff_modify_day_activities(self):
        """Test creating a DayDiff that includes activity changes."""
        from ai_travel_planner.models.itinerary import (
            DayDiff, DayDiffType, ActivityDiff, ActivityDiffType, Activity
        )

        new_activity = Activity(
            name="Dinner",
            description="Local restaurant",
            location="Downtown"
        )

        diff = DayDiff(
            operation=DayDiffType.MODIFY,
            day_number=1,
            activity_diffs=[
                ActivityDiff(operation=ActivityDiffType.ADD, activity=new_activity, position=3),
                ActivityDiff(operation=ActivityDiffType.REMOVE, activity_index=0)
            ]
        )

        assert diff.operation == DayDiffType.MODIFY
        assert len(diff.activity_diffs) == 2
        assert diff.activity_diffs[0].operation == ActivityDiffType.ADD
        assert diff.activity_diffs[1].operation == ActivityDiffType.REMOVE

    def test_day_diff_swap_days(self):
        """Test creating a DayDiff for swapping two days."""
        from ai_travel_planner.models.itinerary import DayDiff, DayDiffType

        diff = DayDiff(
            operation=DayDiffType.SWAP,
            day_number=3,
            swap_with_day=5
        )

        assert diff.operation == DayDiffType.SWAP
        assert diff.day_number == 3
        assert diff.swap_with_day == 5

    def test_day_diff_type_enum_values(self):
        """Test that DayDiffType has expected enum values."""
        from ai_travel_planner.models.itinerary import DayDiffType

        assert DayDiffType.ADD.value == "add"
        assert DayDiffType.REMOVE.value == "remove"
        assert DayDiffType.MODIFY.value == "modify"
        assert DayDiffType.SWAP.value == "swap"

    def test_day_diff_serialization(self):
        """Test that DayDiff serializes correctly."""
        from ai_travel_planner.models.itinerary import DayDiff, DayDiffType, FieldChange

        diff = DayDiff(
            operation=DayDiffType.MODIFY,
            day_number=2,
            field_changes=[
                FieldChange(field="title", old_value="A", new_value="B")
            ]
        )

        data = diff.model_dump()
        assert data["operation"] == "modify"
        assert data["day_number"] == 2
        assert len(data["field_changes"]) == 1

    def test_day_diff_from_dict(self):
        """Test creating DayDiff from dictionary."""
        from ai_travel_planner.models.itinerary import DayDiff

        data = {
            "operation": "remove",
            "day_number": 4
        }

        diff = DayDiff(**data)
        assert diff.operation.value == "remove"
        assert diff.day_number == 4

    def test_day_diff_default_values(self):
        """Test DayDiff default values."""
        from ai_travel_planner.models.itinerary import DayDiff, DayDiffType

        diff = DayDiff(operation=DayDiffType.REMOVE, day_number=1)

        assert diff.day is None
        assert diff.position is None
        assert diff.field_changes == []
        assert diff.activity_diffs == []
        assert diff.swap_with_day is None


class TestItineraryDiff:
    """Tests for ItineraryDiff model - container for all itinerary changes."""

    def test_itinerary_diff_creation_with_summary(self):
        """Test creating an ItineraryDiff with a summary."""
        from ai_travel_planner.models.itinerary import ItineraryDiff

        diff = ItineraryDiff(
            summary="Added beach day and swapped days 4 and 5"
        )

        assert diff.summary == "Added beach day and swapped days 4 and 5"
        assert diff.day_diffs == []
        assert diff.metadata_changes == []

    def test_itinerary_diff_with_day_diffs(self):
        """Test creating an ItineraryDiff with multiple day changes."""
        from ai_travel_planner.models.itinerary import (
            ItineraryDiff, DayDiff, DayDiffType, DayPlan, Activity
        )

        new_day = DayPlan(
            day_number=5,
            title="Beach Day",
            location="Kuta",
            summary="Beach day",
            activities=[Activity(name="Swim", description="Swimming", location="Beach")]
        )

        diff = ItineraryDiff(
            summary="Added new day and removed day 3",
            day_diffs=[
                DayDiff(operation=DayDiffType.ADD, day=new_day, position=4),
                DayDiff(operation=DayDiffType.REMOVE, day_number=3)
            ]
        )

        assert len(diff.day_diffs) == 2
        assert diff.day_diffs[0].operation == DayDiffType.ADD
        assert diff.day_diffs[1].operation == DayDiffType.REMOVE

    def test_itinerary_diff_with_metadata_changes(self):
        """Test creating an ItineraryDiff with metadata field changes."""
        from ai_travel_planner.models.itinerary import ItineraryDiff, FieldChange

        diff = ItineraryDiff(
            summary="Updated trip title and added packing items",
            metadata_changes=[
                FieldChange(field="title", old_value="Japan Trip", new_value="Amazing Japan Adventure"),
                FieldChange(field="budget_estimate", old_value=None, new_value="$5000")
            ]
        )

        assert len(diff.metadata_changes) == 2
        assert diff.metadata_changes[0].field == "title"
        assert diff.metadata_changes[1].is_addition is True

    def test_itinerary_diff_with_all_change_types(self):
        """Test ItineraryDiff with both day and metadata changes."""
        from ai_travel_planner.models.itinerary import (
            ItineraryDiff, DayDiff, DayDiffType, FieldChange
        )

        diff = ItineraryDiff(
            summary="Comprehensive update",
            day_diffs=[
                DayDiff(operation=DayDiffType.SWAP, day_number=2, swap_with_day=3)
            ],
            metadata_changes=[
                FieldChange(field="travelers", old_value=4, new_value=5)
            ]
        )

        assert diff.summary == "Comprehensive update"
        assert len(diff.day_diffs) == 1
        assert len(diff.metadata_changes) == 1

    def test_itinerary_diff_serialization(self):
        """Test that ItineraryDiff serializes correctly to JSON-compatible dict."""
        from ai_travel_planner.models.itinerary import (
            ItineraryDiff, DayDiff, DayDiffType, FieldChange
        )

        diff = ItineraryDiff(
            summary="Test changes",
            day_diffs=[
                DayDiff(operation=DayDiffType.REMOVE, day_number=2)
            ],
            metadata_changes=[
                FieldChange(field="title", old_value="A", new_value="B")
            ]
        )

        data = diff.model_dump()
        assert data["summary"] == "Test changes"
        assert len(data["day_diffs"]) == 1
        assert data["day_diffs"][0]["operation"] == "remove"
        assert len(data["metadata_changes"]) == 1

    def test_itinerary_diff_from_dict(self):
        """Test creating ItineraryDiff from dictionary (JSON parsing)."""
        from ai_travel_planner.models.itinerary import ItineraryDiff

        data = {
            "summary": "Swap days",
            "day_diffs": [
                {"operation": "swap", "day_number": 1, "swap_with_day": 2}
            ],
            "metadata_changes": []
        }

        diff = ItineraryDiff(**data)
        assert diff.summary == "Swap days"
        assert len(diff.day_diffs) == 1
        assert diff.day_diffs[0].swap_with_day == 2

    def test_itinerary_diff_has_changes_property(self):
        """Test has_changes property returns True when there are changes."""
        from ai_travel_planner.models.itinerary import (
            ItineraryDiff, DayDiff, DayDiffType
        )

        empty_diff = ItineraryDiff(summary="No changes")
        assert empty_diff.has_changes is False

        day_diff = ItineraryDiff(
            summary="Day change",
            day_diffs=[DayDiff(operation=DayDiffType.REMOVE, day_number=1)]
        )
        assert day_diff.has_changes is True

    def test_itinerary_diff_change_count_property(self):
        """Test change_count property returns total number of changes."""
        from ai_travel_planner.models.itinerary import (
            ItineraryDiff, DayDiff, DayDiffType, FieldChange
        )

        diff = ItineraryDiff(
            summary="Multiple changes",
            day_diffs=[
                DayDiff(operation=DayDiffType.REMOVE, day_number=1),
                DayDiff(operation=DayDiffType.REMOVE, day_number=2)
            ],
            metadata_changes=[
                FieldChange(field="title", old_value="A", new_value="B")
            ]
        )

        assert diff.change_count == 3

    def test_itinerary_diff_default_values(self):
        """Test ItineraryDiff default values."""
        from ai_travel_planner.models.itinerary import ItineraryDiff

        diff = ItineraryDiff(summary="Test")

        assert diff.day_diffs == []
        assert diff.metadata_changes == []
        assert diff.has_changes is False
        assert diff.change_count == 0
