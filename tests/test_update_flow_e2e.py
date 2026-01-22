"""End-to-end tests for the complete itinerary update flow."""

import json
from unittest.mock import Mock, patch
import pytest

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
from ai_travel_planner.services.itinerary_updater import apply_diff, validate_diff, preview_diff


def create_sample_itinerary() -> Itinerary:
    """Create a realistic sample itinerary for E2E testing."""
    return Itinerary(
        title="Borneo Wildlife Adventure",
        description="A 5-day trip exploring Borneo's wildlife",
        travelers=4,
        days=[
            DayPlan(
                day_number=1,
                title="Arrival in Kota Kinabalu",
                location="Kota Kinabalu",
                summary="Arrive and settle in",
                activities=[
                    Activity(
                        name="Airport Transfer",
                        description="Private transfer from KK International Airport to hotel",
                        location="KK Airport",
                        activity_type="transport",
                    ),
                    Activity(
                        name="Welcome Dinner",
                        description="Seafood dinner at the waterfront",
                        location="Waterfront Esplanade",
                        activity_type="dining",
                    ),
                ],
            ),
            DayPlan(
                day_number=2,
                title="Sepilok Sanctuary Visit",
                location="Sepilok",
                summary="Visit the orangutan and sun bear sanctuaries",
                activities=[
                    Activity(
                        name="Orangutan Rehabilitation Centre",
                        description="Watch orangutan feeding session at 10am",
                        location="Sepilok",
                        activity_type="wildlife",
                        start_time="09:00",
                        end_time="12:00",
                    ),
                    Activity(
                        name="Sun Bear Conservation Centre",
                        description="Learn about sun bear conservation",
                        location="Sepilok",
                        activity_type="wildlife",
                        start_time="14:00",
                        end_time="16:00",
                    ),
                ],
            ),
            DayPlan(
                day_number=3,
                title="Kinabalu National Park",
                location="Mount Kinabalu",
                summary="Explore the national park",
                activities=[
                    Activity(
                        name="Nature Trail Walk",
                        description="Guided walk through the rainforest",
                        location="Kinabalu Park HQ",
                        activity_type="nature",
                    ),
                ],
            ),
        ],
        packing_list=["binoculars", "hiking shoes", "rain jacket"],
    )


class TestEndToEndUpdateFlow:
    """End-to-end tests for the complete update workflow."""

    def test_complete_add_activity_flow(self):
        """Test the complete flow: create diff -> validate -> preview -> apply."""
        # 1. Start with an itinerary
        itinerary = create_sample_itinerary()
        original_day2_activity_count = len(itinerary.days[1].activities)

        # 2. Create a diff (simulating AI response)
        diff = ItineraryDiff(
            summary="Added lunch break to Day 2",
            day_diffs=[
                DayDiff(
                    operation=DayDiffType.MODIFY,
                    day_number=2,
                    activity_diffs=[
                        ActivityDiff(
                            operation=ActivityDiffType.ADD,
                            position=1,  # Between the two existing activities
                            activity=Activity(
                                name="Lunch at Rainforest Discovery Centre",
                                description="Enjoy local cuisine with forest views",
                                location="Sepilok RDC",
                                activity_type="dining",
                                start_time="12:30",
                                end_time="13:30",
                            ),
                        )
                    ],
                )
            ],
        )

        # 3. Validate the diff
        errors = validate_diff(itinerary, diff)
        assert len(errors) == 0, f"Validation should pass: {errors}"

        # 4. Preview the diff
        preview = preview_diff(itinerary, diff)
        assert preview["change_count"] == 1
        assert "Lunch" in preview["changes"][0]["description"]

        # 5. Apply the diff
        updated = apply_diff(itinerary, diff)

        # 6. Verify the result
        assert len(updated.days[1].activities) == original_day2_activity_count + 1
        assert updated.days[1].activities[1].name == "Lunch at Rainforest Discovery Centre"
        # Original itinerary unchanged
        assert len(itinerary.days[1].activities) == original_day2_activity_count

    def test_complete_swap_days_flow(self):
        """Test swapping two days end-to-end."""
        itinerary = create_sample_itinerary()
        original_day2_title = itinerary.days[1].title
        original_day3_title = itinerary.days[2].title

        diff = ItineraryDiff(
            summary="Swapped Day 2 and Day 3 for better logistics",
            day_diffs=[
                DayDiff(
                    operation=DayDiffType.SWAP,
                    day_number=2,
                    swap_with_day=3,
                )
            ],
        )

        # Validate
        errors = validate_diff(itinerary, diff)
        assert len(errors) == 0

        # Apply
        updated = apply_diff(itinerary, diff)

        # Verify swap happened
        assert updated.days[1].title == original_day3_title
        assert updated.days[2].title == original_day2_title
        # Day numbers should be correct
        assert updated.days[1].day_number == 2
        assert updated.days[2].day_number == 3

    def test_complete_remove_and_modify_flow(self):
        """Test combining remove activity and modify day in one diff."""
        itinerary = create_sample_itinerary()

        diff = ItineraryDiff(
            summary="Reorganized Day 1",
            day_diffs=[
                DayDiff(
                    operation=DayDiffType.MODIFY,
                    day_number=1,
                    field_changes=[
                        FieldChange(
                            field="title",
                            old_value="Arrival in Kota Kinabalu",
                            new_value="Welcome to Borneo",
                        )
                    ],
                    activity_diffs=[
                        ActivityDiff(
                            operation=ActivityDiffType.REMOVE,
                            activity_index=0,  # Remove airport transfer
                        ),
                        ActivityDiff(
                            operation=ActivityDiffType.ADD,
                            position=0,
                            activity=Activity(
                                name="Private Airport Pickup",
                                description="VIP pickup with welcome drinks",
                                location="KK Airport",
                                activity_type="transport",
                            ),
                        ),
                    ],
                )
            ],
        )

        errors = validate_diff(itinerary, diff)
        assert len(errors) == 0

        updated = apply_diff(itinerary, diff)

        assert updated.days[0].title == "Welcome to Borneo"
        assert updated.days[0].activities[0].name == "Private Airport Pickup"

    def test_complete_metadata_update_flow(self):
        """Test updating itinerary metadata."""
        itinerary = create_sample_itinerary()

        diff = ItineraryDiff(
            summary="Updated trip details",
            day_diffs=[],
            metadata_changes=[
                FieldChange(
                    field="title",
                    old_value="Borneo Wildlife Adventure",
                    new_value="Ultimate Borneo Wildlife Safari",
                ),
                FieldChange(
                    field="packing_list",
                    old_value=["binoculars", "hiking shoes", "rain jacket"],
                    new_value=["binoculars", "hiking shoes", "rain jacket", "camera", "insect repellent"],
                ),
            ],
        )

        errors = validate_diff(itinerary, diff)
        assert len(errors) == 0

        updated = apply_diff(itinerary, diff)

        assert updated.title == "Ultimate Borneo Wildlife Safari"
        assert "camera" in updated.packing_list
        assert "insect repellent" in updated.packing_list


class TestErrorHandling:
    """Tests for error handling in the update flow."""

    def test_invalid_day_reference_caught(self):
        """Test that referencing non-existent day is caught by validation."""
        itinerary = create_sample_itinerary()

        diff = ItineraryDiff(
            summary="Invalid update",
            day_diffs=[
                DayDiff(
                    operation=DayDiffType.MODIFY,
                    day_number=99,  # Doesn't exist
                    field_changes=[FieldChange(field="title", old_value="X", new_value="Y")],
                )
            ],
        )

        errors = validate_diff(itinerary, diff)
        assert len(errors) > 0
        assert "99" in errors[0]

    def test_invalid_activity_index_caught(self):
        """Test that referencing non-existent activity is caught."""
        itinerary = create_sample_itinerary()

        diff = ItineraryDiff(
            summary="Invalid update",
            day_diffs=[
                DayDiff(
                    operation=DayDiffType.MODIFY,
                    day_number=1,
                    activity_diffs=[
                        ActivityDiff(
                            operation=ActivityDiffType.REMOVE,
                            activity_index=99,  # Doesn't exist
                        )
                    ],
                )
            ],
        )

        errors = validate_diff(itinerary, diff)
        assert len(errors) > 0
        assert "activity" in errors[0].lower()

    def test_empty_diff_handled_gracefully(self):
        """Test that an empty diff (no changes) works correctly."""
        itinerary = create_sample_itinerary()

        diff = ItineraryDiff(
            summary="No changes needed",
            day_diffs=[],
            metadata_changes=[],
        )

        errors = validate_diff(itinerary, diff)
        assert len(errors) == 0

        updated = apply_diff(itinerary, diff)

        # Should be equivalent to original
        assert updated.title == itinerary.title
        assert len(updated.days) == len(itinerary.days)


class TestAgentIntegrationMocked:
    """Integration tests with mocked AI agents."""

    @patch("ai_travel_planner.agents.claude_agent.anthropic.Anthropic")
    def test_claude_agent_update_flow(self, mock_anthropic):
        """Test complete flow with ClaudeAgent (mocked)."""
        from ai_travel_planner.agents.claude_agent import ClaudeAgent

        # Setup mock
        mock_client = Mock()
        mock_anthropic.return_value = mock_client

        ai_response = json.dumps({
            "summary": "Added beach activity",
            "day_diffs": [
                {
                    "operation": "modify",
                    "day_number": 1,
                    "activity_diffs": [
                        {
                            "operation": "add",
                            "position": 2,
                            "activity": {
                                "name": "Beach Visit",
                                "description": "Relax at the beach",
                                "location": "Tanjung Aru",
                                "activity_type": "relaxation",
                            }
                        }
                    ]
                }
            ],
            "metadata_changes": []
        })

        mock_response = Mock()
        mock_response.content = [Mock(text=ai_response)]
        mock_client.messages.create.return_value = mock_response

        # Execute flow
        agent = ClaudeAgent(api_key="test-key")
        itinerary = create_sample_itinerary()

        # 1. Agent generates diff
        diff = agent.generate_itinerary_update(
            current_itinerary=itinerary,
            update_request="Add a beach visit to day 1",
        )

        # 2. Validate
        errors = validate_diff(itinerary, diff)
        assert len(errors) == 0

        # 3. Apply
        updated = apply_diff(itinerary, diff)

        # 4. Verify
        assert len(updated.days[0].activities) == 3
        assert updated.days[0].activities[2].name == "Beach Visit"
