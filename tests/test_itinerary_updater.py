"""Tests for the itinerary_updater service."""

import pytest
from copy import deepcopy

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


def create_sample_itinerary() -> Itinerary:
    """Create a sample itinerary for testing."""
    return Itinerary(
        title="Borneo Adventure",
        description="A 3-day wildlife trip",
        days=[
            DayPlan(
                day_number=1,
                title="Arrival Day",
                location="Kota Kinabalu",
                summary="Arrive and explore the city",
                activities=[
                    Activity(
                        name="Airport Transfer",
                        description="Transfer from airport to hotel",
                        location="KK Airport",
                        activity_type="transport",
                    ),
                    Activity(
                        name="City Walk",
                        description="Evening walk around the city",
                        location="City Center",
                        activity_type="sightseeing",
                    ),
                ],
            ),
            DayPlan(
                day_number=2,
                title="Wildlife Day",
                location="Sepilok",
                summary="Visit orangutan sanctuary",
                activities=[
                    Activity(
                        name="Orangutan Sanctuary",
                        description="Morning visit to see orangutans",
                        location="Sepilok",
                        activity_type="wildlife",
                    ),
                    Activity(
                        name="Sun Bear Center",
                        description="Afternoon visit to sun bears",
                        location="Sepilok",
                        activity_type="wildlife",
                    ),
                ],
            ),
            DayPlan(
                day_number=3,
                title="Departure Day",
                location="Kota Kinabalu",
                summary="Final morning and departure",
                activities=[
                    Activity(
                        name="Morning Market",
                        description="Visit the local market",
                        location="Filipino Market",
                        activity_type="shopping",
                    ),
                ],
            ),
        ],
    )


class TestApplyDiffAddActivity:
    """Tests for apply_diff - adding activities."""

    def test_add_activity_to_day(self):
        """Test adding a new activity to a day."""
        from ai_travel_planner.services.itinerary_updater import apply_diff

        itinerary = create_sample_itinerary()
        new_activity = Activity(
            name="Beach Sunset",
            description="Watch sunset at the beach",
            location="Tanjung Aru",
            activity_type="relaxation",
        )

        diff = ItineraryDiff(
            summary="Added beach sunset to Day 1",
            day_diffs=[
                DayDiff(
                    operation=DayDiffType.MODIFY,
                    day_number=1,
                    activity_diffs=[
                        ActivityDiff(
                            operation=ActivityDiffType.ADD,
                            position=2,
                            activity=new_activity,
                        )
                    ],
                )
            ],
        )

        result = apply_diff(itinerary, diff)

        assert len(result.days[0].activities) == 3
        assert result.days[0].activities[2].name == "Beach Sunset"

    def test_add_activity_at_beginning(self):
        """Test adding an activity at position 0."""
        from ai_travel_planner.services.itinerary_updater import apply_diff

        itinerary = create_sample_itinerary()
        new_activity = Activity(
            name="Early Breakfast",
            description="Breakfast at hotel",
            location="Hotel",
            activity_type="dining",
        )

        diff = ItineraryDiff(
            summary="Added breakfast to Day 1",
            day_diffs=[
                DayDiff(
                    operation=DayDiffType.MODIFY,
                    day_number=1,
                    activity_diffs=[
                        ActivityDiff(
                            operation=ActivityDiffType.ADD,
                            position=0,
                            activity=new_activity,
                        )
                    ],
                )
            ],
        )

        result = apply_diff(itinerary, diff)

        assert len(result.days[0].activities) == 3
        assert result.days[0].activities[0].name == "Early Breakfast"
        assert result.days[0].activities[1].name == "Airport Transfer"


class TestApplyDiffRemoveActivity:
    """Tests for apply_diff - removing activities."""

    def test_remove_activity_from_day(self):
        """Test removing an activity from a day."""
        from ai_travel_planner.services.itinerary_updater import apply_diff

        itinerary = create_sample_itinerary()

        diff = ItineraryDiff(
            summary="Removed City Walk from Day 1",
            day_diffs=[
                DayDiff(
                    operation=DayDiffType.MODIFY,
                    day_number=1,
                    activity_diffs=[
                        ActivityDiff(
                            operation=ActivityDiffType.REMOVE,
                            activity_index=1,
                        )
                    ],
                )
            ],
        )

        result = apply_diff(itinerary, diff)

        assert len(result.days[0].activities) == 1
        assert result.days[0].activities[0].name == "Airport Transfer"

    def test_remove_first_activity(self):
        """Test removing the first activity."""
        from ai_travel_planner.services.itinerary_updater import apply_diff

        itinerary = create_sample_itinerary()

        diff = ItineraryDiff(
            summary="Removed Airport Transfer from Day 1",
            day_diffs=[
                DayDiff(
                    operation=DayDiffType.MODIFY,
                    day_number=1,
                    activity_diffs=[
                        ActivityDiff(
                            operation=ActivityDiffType.REMOVE,
                            activity_index=0,
                        )
                    ],
                )
            ],
        )

        result = apply_diff(itinerary, diff)

        assert len(result.days[0].activities) == 1
        assert result.days[0].activities[0].name == "City Walk"


class TestApplyDiffModifyActivity:
    """Tests for apply_diff - modifying activities."""

    def test_modify_activity_field(self):
        """Test modifying a single field of an activity."""
        from ai_travel_planner.services.itinerary_updater import apply_diff

        itinerary = create_sample_itinerary()

        diff = ItineraryDiff(
            summary="Updated City Walk description",
            day_diffs=[
                DayDiff(
                    operation=DayDiffType.MODIFY,
                    day_number=1,
                    activity_diffs=[
                        ActivityDiff(
                            operation=ActivityDiffType.MODIFY,
                            activity_index=1,
                            field_changes=[
                                FieldChange(
                                    field="description",
                                    old_value="Evening walk around the city",
                                    new_value="Guided evening walking tour of historic city center",
                                )
                            ],
                        )
                    ],
                )
            ],
        )

        result = apply_diff(itinerary, diff)

        assert result.days[0].activities[1].description == "Guided evening walking tour of historic city center"

    def test_modify_multiple_activity_fields(self):
        """Test modifying multiple fields of an activity."""
        from ai_travel_planner.services.itinerary_updater import apply_diff

        itinerary = create_sample_itinerary()

        diff = ItineraryDiff(
            summary="Updated activity details",
            day_diffs=[
                DayDiff(
                    operation=DayDiffType.MODIFY,
                    day_number=1,
                    activity_diffs=[
                        ActivityDiff(
                            operation=ActivityDiffType.MODIFY,
                            activity_index=1,
                            field_changes=[
                                FieldChange(field="name", old_value="City Walk", new_value="Night Market Tour"),
                                FieldChange(field="location", old_value="City Center", new_value="Gaya Street"),
                            ],
                        )
                    ],
                )
            ],
        )

        result = apply_diff(itinerary, diff)

        assert result.days[0].activities[1].name == "Night Market Tour"
        assert result.days[0].activities[1].location == "Gaya Street"


class TestApplyDiffModifyDay:
    """Tests for apply_diff - modifying day properties."""

    def test_modify_day_title(self):
        """Test modifying a day's title."""
        from ai_travel_planner.services.itinerary_updater import apply_diff

        itinerary = create_sample_itinerary()

        diff = ItineraryDiff(
            summary="Updated Day 1 title",
            day_diffs=[
                DayDiff(
                    operation=DayDiffType.MODIFY,
                    day_number=1,
                    field_changes=[
                        FieldChange(field="title", old_value="Arrival Day", new_value="Welcome to Borneo"),
                    ],
                )
            ],
        )

        result = apply_diff(itinerary, diff)

        assert result.days[0].title == "Welcome to Borneo"

    def test_modify_day_location_and_summary(self):
        """Test modifying multiple day fields."""
        from ai_travel_planner.services.itinerary_updater import apply_diff

        itinerary = create_sample_itinerary()

        diff = ItineraryDiff(
            summary="Updated Day 2 details",
            day_diffs=[
                DayDiff(
                    operation=DayDiffType.MODIFY,
                    day_number=2,
                    field_changes=[
                        FieldChange(field="location", old_value="Sepilok", new_value="Sandakan"),
                        FieldChange(field="summary", old_value="Visit orangutan sanctuary", new_value="Full day wildlife adventure"),
                    ],
                )
            ],
        )

        result = apply_diff(itinerary, diff)

        assert result.days[1].location == "Sandakan"
        assert result.days[1].summary == "Full day wildlife adventure"


class TestApplyDiffSwapDays:
    """Tests for apply_diff - swapping days."""

    def test_swap_two_days(self):
        """Test swapping two days."""
        from ai_travel_planner.services.itinerary_updater import apply_diff

        itinerary = create_sample_itinerary()
        original_day1_title = itinerary.days[0].title
        original_day2_title = itinerary.days[1].title

        diff = ItineraryDiff(
            summary="Swapped Day 1 and Day 2",
            day_diffs=[
                DayDiff(
                    operation=DayDiffType.SWAP,
                    day_number=1,
                    swap_with_day=2,
                )
            ],
        )

        result = apply_diff(itinerary, diff)

        # Day numbers should remain 1, 2, 3 but content swapped
        assert result.days[0].day_number == 1
        assert result.days[1].day_number == 2
        assert result.days[0].title == original_day2_title
        assert result.days[1].title == original_day1_title

    def test_swap_non_adjacent_days(self):
        """Test swapping non-adjacent days."""
        from ai_travel_planner.services.itinerary_updater import apply_diff

        itinerary = create_sample_itinerary()
        original_day1_title = itinerary.days[0].title
        original_day3_title = itinerary.days[2].title

        diff = ItineraryDiff(
            summary="Swapped Day 1 and Day 3",
            day_diffs=[
                DayDiff(
                    operation=DayDiffType.SWAP,
                    day_number=1,
                    swap_with_day=3,
                )
            ],
        )

        result = apply_diff(itinerary, diff)

        assert result.days[0].title == original_day3_title
        assert result.days[2].title == original_day1_title


class TestApplyDiffAddRemoveDay:
    """Tests for apply_diff - adding and removing days."""

    def test_add_new_day(self):
        """Test adding a new day to the itinerary."""
        from ai_travel_planner.services.itinerary_updater import apply_diff

        itinerary = create_sample_itinerary()

        new_day = DayPlan(
            day_number=4,
            title="Beach Day",
            location="Manukan Island",
            summary="Day trip to the island",
            activities=[
                Activity(
                    name="Island Hopping",
                    description="Boat trip to the island",
                    location="Jesselton Point",
                    activity_type="adventure",
                )
            ],
        )

        diff = ItineraryDiff(
            summary="Added Beach Day",
            day_diffs=[
                DayDiff(
                    operation=DayDiffType.ADD,
                    position=4,
                    day=new_day,
                )
            ],
        )

        result = apply_diff(itinerary, diff)

        assert len(result.days) == 4
        assert result.days[3].title == "Beach Day"
        assert result.days[3].day_number == 4

    def test_add_day_in_middle(self):
        """Test inserting a day in the middle of the itinerary."""
        from ai_travel_planner.services.itinerary_updater import apply_diff

        itinerary = create_sample_itinerary()

        new_day = DayPlan(
            day_number=2,
            title="Rest Day",
            location="Kota Kinabalu",
            summary="Relaxation day",
            activities=[],
        )

        diff = ItineraryDiff(
            summary="Inserted Rest Day after Day 1",
            day_diffs=[
                DayDiff(
                    operation=DayDiffType.ADD,
                    position=2,
                    day=new_day,
                )
            ],
        )

        result = apply_diff(itinerary, diff)

        assert len(result.days) == 4
        assert result.days[1].title == "Rest Day"
        # Day numbers should be renumbered
        assert result.days[0].day_number == 1
        assert result.days[1].day_number == 2
        assert result.days[2].day_number == 3
        assert result.days[3].day_number == 4

    def test_remove_day(self):
        """Test removing a day from the itinerary."""
        from ai_travel_planner.services.itinerary_updater import apply_diff

        itinerary = create_sample_itinerary()

        diff = ItineraryDiff(
            summary="Removed Day 2",
            day_diffs=[
                DayDiff(
                    operation=DayDiffType.REMOVE,
                    day_number=2,
                )
            ],
        )

        result = apply_diff(itinerary, diff)

        assert len(result.days) == 2
        # Day numbers should be renumbered
        assert result.days[0].day_number == 1
        assert result.days[0].title == "Arrival Day"
        assert result.days[1].day_number == 2
        assert result.days[1].title == "Departure Day"


class TestApplyDiffMetadata:
    """Tests for apply_diff - modifying itinerary metadata."""

    def test_modify_itinerary_title(self):
        """Test modifying the itinerary title."""
        from ai_travel_planner.services.itinerary_updater import apply_diff

        itinerary = create_sample_itinerary()

        diff = ItineraryDiff(
            summary="Updated trip title",
            day_diffs=[],
            metadata_changes=[
                FieldChange(field="title", old_value="Borneo Adventure", new_value="Borneo Wildlife Safari"),
            ],
        )

        result = apply_diff(itinerary, diff)

        assert result.title == "Borneo Wildlife Safari"

    def test_modify_packing_list(self):
        """Test modifying the packing list."""
        from ai_travel_planner.services.itinerary_updater import apply_diff

        itinerary = create_sample_itinerary()
        itinerary.packing_list = ["clothes", "camera"]

        diff = ItineraryDiff(
            summary="Added binoculars to packing list",
            day_diffs=[],
            metadata_changes=[
                FieldChange(
                    field="packing_list",
                    old_value=["clothes", "camera"],
                    new_value=["clothes", "camera", "binoculars"],
                ),
            ],
        )

        result = apply_diff(itinerary, diff)

        assert "binoculars" in result.packing_list


class TestApplyDiffComplex:
    """Tests for apply_diff - complex multi-change scenarios."""

    def test_multiple_changes_in_single_diff(self):
        """Test applying multiple changes at once."""
        from ai_travel_planner.services.itinerary_updater import apply_diff

        itinerary = create_sample_itinerary()

        diff = ItineraryDiff(
            summary="Multiple updates",
            day_diffs=[
                # Modify Day 1 title
                DayDiff(
                    operation=DayDiffType.MODIFY,
                    day_number=1,
                    field_changes=[
                        FieldChange(field="title", old_value="Arrival Day", new_value="Welcome Day"),
                    ],
                ),
                # Add activity to Day 2
                DayDiff(
                    operation=DayDiffType.MODIFY,
                    day_number=2,
                    activity_diffs=[
                        ActivityDiff(
                            operation=ActivityDiffType.ADD,
                            position=2,
                            activity=Activity(
                                name="Lunch Break",
                                description="Lunch at local restaurant",
                                location="Sepilok",
                                activity_type="dining",
                            ),
                        )
                    ],
                ),
            ],
            metadata_changes=[
                FieldChange(field="description", old_value="A 3-day wildlife trip", new_value="An amazing 3-day wildlife adventure"),
            ],
        )

        result = apply_diff(itinerary, diff)

        assert result.days[0].title == "Welcome Day"
        assert len(result.days[1].activities) == 3
        assert result.days[1].activities[2].name == "Lunch Break"
        assert result.description == "An amazing 3-day wildlife adventure"


class TestApplyDiffDoesNotMutate:
    """Tests to ensure apply_diff doesn't mutate the original."""

    def test_original_itinerary_unchanged(self):
        """Test that the original itinerary is not modified."""
        from ai_travel_planner.services.itinerary_updater import apply_diff

        itinerary = create_sample_itinerary()
        original_title = itinerary.days[0].title

        diff = ItineraryDiff(
            summary="Updated Day 1",
            day_diffs=[
                DayDiff(
                    operation=DayDiffType.MODIFY,
                    day_number=1,
                    field_changes=[
                        FieldChange(field="title", old_value="Arrival Day", new_value="New Title"),
                    ],
                )
            ],
        )

        result = apply_diff(itinerary, diff)

        # Original should be unchanged
        assert itinerary.days[0].title == original_title
        # Result should have the new value
        assert result.days[0].title == "New Title"


class TestValidateDiff:
    """Tests for validate_diff function."""

    def test_valid_diff_passes(self):
        """Test that a valid diff passes validation."""
        from ai_travel_planner.services.itinerary_updater import validate_diff

        itinerary = create_sample_itinerary()
        diff = ItineraryDiff(
            summary="Valid change",
            day_diffs=[
                DayDiff(
                    operation=DayDiffType.MODIFY,
                    day_number=1,
                    field_changes=[FieldChange(field="title", old_value="Arrival Day", new_value="New Title")],
                )
            ],
        )

        errors = validate_diff(itinerary, diff)
        assert len(errors) == 0

    def test_invalid_day_number(self):
        """Test that referencing non-existent day fails validation."""
        from ai_travel_planner.services.itinerary_updater import validate_diff

        itinerary = create_sample_itinerary()
        diff = ItineraryDiff(
            summary="Invalid change",
            day_diffs=[
                DayDiff(
                    operation=DayDiffType.MODIFY,
                    day_number=99,
                    field_changes=[FieldChange(field="title", old_value="X", new_value="Y")],
                )
            ],
        )

        errors = validate_diff(itinerary, diff)
        assert len(errors) > 0
        assert "day 99" in errors[0].lower()

    def test_invalid_activity_index(self):
        """Test that referencing non-existent activity fails validation."""
        from ai_travel_planner.services.itinerary_updater import validate_diff

        itinerary = create_sample_itinerary()
        diff = ItineraryDiff(
            summary="Invalid change",
            day_diffs=[
                DayDiff(
                    operation=DayDiffType.MODIFY,
                    day_number=1,
                    activity_diffs=[
                        ActivityDiff(
                            operation=ActivityDiffType.REMOVE,
                            activity_index=99,
                        )
                    ],
                )
            ],
        )

        errors = validate_diff(itinerary, diff)
        assert len(errors) > 0
        assert "activity" in errors[0].lower()


class TestPreviewDiff:
    """Tests for preview_diff function."""

    def test_preview_shows_changes(self):
        """Test that preview shows what will change."""
        from ai_travel_planner.services.itinerary_updater import preview_diff

        itinerary = create_sample_itinerary()
        diff = ItineraryDiff(
            summary="Updated Day 1 title",
            day_diffs=[
                DayDiff(
                    operation=DayDiffType.MODIFY,
                    day_number=1,
                    field_changes=[
                        FieldChange(field="title", old_value="Arrival Day", new_value="Welcome Day"),
                    ],
                )
            ],
        )

        preview = preview_diff(itinerary, diff)

        assert "summary" in preview
        assert "changes" in preview
        assert len(preview["changes"]) > 0

    def test_preview_includes_day_changes(self):
        """Test that preview includes day-level change details."""
        from ai_travel_planner.services.itinerary_updater import preview_diff

        itinerary = create_sample_itinerary()
        diff = ItineraryDiff(
            summary="Swapped days",
            day_diffs=[
                DayDiff(
                    operation=DayDiffType.SWAP,
                    day_number=1,
                    swap_with_day=2,
                )
            ],
        )

        preview = preview_diff(itinerary, diff)

        # Should describe the swap
        assert any("swap" in str(c).lower() for c in preview["changes"])
