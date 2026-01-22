"""Tests for ITINERARY_UPDATE_PROMPT output parsing and generate_itinerary_update method."""

import inspect
import json
import pytest
from abc import abstractmethod

from ai_travel_planner.agents.base import extract_json_from_response, TravelAgent
from ai_travel_planner.models.itinerary import (
    Itinerary,
    ItineraryDiff,
    DayDiff,
    DayDiffType,
    ActivityDiff,
    ActivityDiffType,
    FieldChange,
    Activity,
    DayPlan,
)


class TestUpdatePromptOutputParsing:
    """Tests for parsing AI responses from the update prompt."""

    def test_parse_simple_modify_day_response(self):
        """Test parsing a response that modifies a single day's title."""
        response = '''```json
{
    "summary": "Changed Day 2 title",
    "day_diffs": [
        {
            "operation": "modify",
            "day_number": 2,
            "field_changes": [
                {"field": "title", "old_value": "Beach Day", "new_value": "Adventure Day"}
            ]
        }
    ],
    "metadata_changes": []
}
```'''
        json_str = extract_json_from_response(response)
        diff = ItineraryDiff.model_validate_json(json_str)

        assert diff.summary == "Changed Day 2 title"
        assert len(diff.day_diffs) == 1
        assert diff.day_diffs[0].operation == DayDiffType.MODIFY
        assert diff.day_diffs[0].day_number == 2
        assert diff.day_diffs[0].field_changes[0].field == "title"
        assert diff.day_diffs[0].field_changes[0].new_value == "Adventure Day"

    def test_parse_add_day_response(self):
        """Test parsing a response that adds a new day."""
        response = '''{
    "summary": "Added beach day as Day 5",
    "day_diffs": [
        {
            "operation": "add",
            "position": 5,
            "day": {
                "day_number": 5,
                "title": "Beach Relaxation",
                "location": "Kota Kinabalu Beach",
                "summary": "A relaxing day at the beach",
                "activities": [
                    {
                        "name": "Swimming",
                        "description": "Morning swim in crystal clear waters",
                        "location": "Tanjung Aru Beach",
                        "activity_type": "relaxation"
                    }
                ]
            }
        }
    ],
    "metadata_changes": []
}'''
        json_str = extract_json_from_response(response)
        diff = ItineraryDiff.model_validate_json(json_str)

        assert diff.summary == "Added beach day as Day 5"
        assert len(diff.day_diffs) == 1
        assert diff.day_diffs[0].operation == DayDiffType.ADD
        assert diff.day_diffs[0].position == 5
        assert diff.day_diffs[0].day is not None
        assert diff.day_diffs[0].day.title == "Beach Relaxation"
        assert len(diff.day_diffs[0].day.activities) == 1

    def test_parse_remove_day_response(self):
        """Test parsing a response that removes a day."""
        response = '''{
    "summary": "Removed Day 3 (rest day)",
    "day_diffs": [
        {
            "operation": "remove",
            "day_number": 3
        }
    ],
    "metadata_changes": []
}'''
        json_str = extract_json_from_response(response)
        diff = ItineraryDiff.model_validate_json(json_str)

        assert diff.summary == "Removed Day 3 (rest day)"
        assert len(diff.day_diffs) == 1
        assert diff.day_diffs[0].operation == DayDiffType.REMOVE
        assert diff.day_diffs[0].day_number == 3

    def test_parse_swap_days_response(self):
        """Test parsing a response that swaps two days."""
        response = '''{
    "summary": "Swapped Day 2 and Day 4",
    "day_diffs": [
        {
            "operation": "swap",
            "day_number": 2,
            "swap_with_day": 4
        }
    ],
    "metadata_changes": []
}'''
        json_str = extract_json_from_response(response)
        diff = ItineraryDiff.model_validate_json(json_str)

        assert diff.summary == "Swapped Day 2 and Day 4"
        assert len(diff.day_diffs) == 1
        assert diff.day_diffs[0].operation == DayDiffType.SWAP
        assert diff.day_diffs[0].day_number == 2
        assert diff.day_diffs[0].swap_with_day == 4

    def test_parse_add_activity_response(self):
        """Test parsing a response that adds an activity to a day."""
        response = '''{
    "summary": "Added dinner at Local Restaurant to Day 2",
    "day_diffs": [
        {
            "operation": "modify",
            "day_number": 2,
            "activity_diffs": [
                {
                    "operation": "add",
                    "position": 3,
                    "activity": {
                        "name": "Dinner at Seafood Market",
                        "description": "Fresh seafood dinner at the night market",
                        "location": "Filipino Market",
                        "activity_type": "dining",
                        "start_time": "19:00",
                        "end_time": "21:00"
                    }
                }
            ]
        }
    ],
    "metadata_changes": []
}'''
        json_str = extract_json_from_response(response)
        diff = ItineraryDiff.model_validate_json(json_str)

        assert len(diff.day_diffs) == 1
        assert diff.day_diffs[0].operation == DayDiffType.MODIFY
        assert len(diff.day_diffs[0].activity_diffs) == 1
        activity_diff = diff.day_diffs[0].activity_diffs[0]
        assert activity_diff.operation == ActivityDiffType.ADD
        assert activity_diff.position == 3
        assert activity_diff.activity.name == "Dinner at Seafood Market"

    def test_parse_remove_activity_response(self):
        """Test parsing a response that removes an activity from a day."""
        response = '''{
    "summary": "Removed museum visit from Day 1",
    "day_diffs": [
        {
            "operation": "modify",
            "day_number": 1,
            "activity_diffs": [
                {
                    "operation": "remove",
                    "activity_index": 2
                }
            ]
        }
    ],
    "metadata_changes": []
}'''
        json_str = extract_json_from_response(response)
        diff = ItineraryDiff.model_validate_json(json_str)

        activity_diff = diff.day_diffs[0].activity_diffs[0]
        assert activity_diff.operation == ActivityDiffType.REMOVE
        assert activity_diff.activity_index == 2

    def test_parse_modify_activity_response(self):
        """Test parsing a response that modifies an activity's fields."""
        response = '''{
    "summary": "Updated temple visit timing",
    "day_diffs": [
        {
            "operation": "modify",
            "day_number": 3,
            "activity_diffs": [
                {
                    "operation": "modify",
                    "activity_index": 0,
                    "field_changes": [
                        {"field": "start_time", "old_value": "09:00", "new_value": "07:00"},
                        {"field": "description", "old_value": "Visit temple", "new_value": "Early morning visit to avoid crowds"}
                    ]
                }
            ]
        }
    ],
    "metadata_changes": []
}'''
        json_str = extract_json_from_response(response)
        diff = ItineraryDiff.model_validate_json(json_str)

        activity_diff = diff.day_diffs[0].activity_diffs[0]
        assert activity_diff.operation == ActivityDiffType.MODIFY
        assert activity_diff.activity_index == 0
        assert len(activity_diff.field_changes) == 2
        assert activity_diff.field_changes[0].field == "start_time"
        assert activity_diff.field_changes[0].new_value == "07:00"

    def test_parse_metadata_change_response(self):
        """Test parsing a response that modifies itinerary metadata."""
        response = '''{
    "summary": "Updated trip title and added packing item",
    "day_diffs": [],
    "metadata_changes": [
        {"field": "title", "old_value": "Borneo Trip", "new_value": "Borneo Wildlife Adventure"},
        {"field": "packing_list", "old_value": ["clothes"], "new_value": ["clothes", "binoculars"]}
    ]
}'''
        json_str = extract_json_from_response(response)
        diff = ItineraryDiff.model_validate_json(json_str)

        assert diff.summary == "Updated trip title and added packing item"
        assert len(diff.day_diffs) == 0
        assert len(diff.metadata_changes) == 2
        assert diff.metadata_changes[0].field == "title"
        assert diff.metadata_changes[0].new_value == "Borneo Wildlife Adventure"

    def test_parse_complex_multi_change_response(self):
        """Test parsing a response with multiple types of changes."""
        response = '''{
    "summary": "Reorganized trip: swapped days 2-3, added activity to day 1, updated title",
    "day_diffs": [
        {
            "operation": "swap",
            "day_number": 2,
            "swap_with_day": 3
        },
        {
            "operation": "modify",
            "day_number": 1,
            "activity_diffs": [
                {
                    "operation": "add",
                    "position": 2,
                    "activity": {
                        "name": "Sunset viewing",
                        "description": "Watch sunset from Signal Hill",
                        "location": "Signal Hill",
                        "activity_type": "sightseeing"
                    }
                }
            ]
        }
    ],
    "metadata_changes": [
        {"field": "title", "old_value": "Trip", "new_value": "Borneo Explorer"}
    ]
}'''
        json_str = extract_json_from_response(response)
        diff = ItineraryDiff.model_validate_json(json_str)

        assert diff.has_changes
        assert diff.change_count == 3
        assert len(diff.day_diffs) == 2
        assert len(diff.metadata_changes) == 1

    def test_parse_empty_changes_response(self):
        """Test parsing a response with no changes (user request was unclear)."""
        response = '''{
    "summary": "No changes needed - the itinerary already includes this",
    "day_diffs": [],
    "metadata_changes": []
}'''
        json_str = extract_json_from_response(response)
        diff = ItineraryDiff.model_validate_json(json_str)

        assert not diff.has_changes
        assert diff.change_count == 0
        assert diff.summary == "No changes needed - the itinerary already includes this"

    def test_parse_response_with_markdown_wrapper(self):
        """Test parsing response wrapped in markdown code block."""
        response = '''Here are the changes to your itinerary:

```json
{
    "summary": "Added restaurant",
    "day_diffs": [
        {
            "operation": "modify",
            "day_number": 1,
            "activity_diffs": [{"operation": "add", "position": 0, "activity": {"name": "Breakfast", "description": "Local breakfast", "location": "Hotel", "activity_type": "dining"}}]
        }
    ],
    "metadata_changes": []
}
```

Let me know if you'd like any other changes!'''
        json_str = extract_json_from_response(response)
        diff = ItineraryDiff.model_validate_json(json_str)

        assert diff.summary == "Added restaurant"
        assert len(diff.day_diffs) == 1


class TestUpdatePromptTemplate:
    """Tests for the ITINERARY_UPDATE_PROMPT template itself."""

    def test_template_exists(self):
        """Test that ITINERARY_UPDATE_PROMPT is defined."""
        from ai_travel_planner.agents.base import ITINERARY_UPDATE_PROMPT
        assert ITINERARY_UPDATE_PROMPT is not None
        assert len(ITINERARY_UPDATE_PROMPT) > 0

    def test_template_has_required_placeholders(self):
        """Test that template contains required placeholders."""
        from ai_travel_planner.agents.base import ITINERARY_UPDATE_PROMPT
        assert "{current_itinerary}" in ITINERARY_UPDATE_PROMPT
        assert "{update_request}" in ITINERARY_UPDATE_PROMPT

    def test_template_describes_diff_structure(self):
        """Test that template includes ItineraryDiff JSON structure."""
        from ai_travel_planner.agents.base import ITINERARY_UPDATE_PROMPT
        # Should describe the expected output format
        assert "summary" in ITINERARY_UPDATE_PROMPT
        assert "day_diffs" in ITINERARY_UPDATE_PROMPT
        assert "metadata_changes" in ITINERARY_UPDATE_PROMPT

    def test_template_includes_operation_types(self):
        """Test that template documents available operations."""
        from ai_travel_planner.agents.base import ITINERARY_UPDATE_PROMPT
        # Should mention the operation types
        assert "add" in ITINERARY_UPDATE_PROMPT.lower()
        assert "remove" in ITINERARY_UPDATE_PROMPT.lower()
        assert "modify" in ITINERARY_UPDATE_PROMPT.lower()
        assert "swap" in ITINERARY_UPDATE_PROMPT.lower()

    def test_template_can_be_formatted(self):
        """Test that template can be formatted with sample data."""
        from ai_travel_planner.agents.base import ITINERARY_UPDATE_PROMPT
        sample_itinerary = '{"title": "Test Trip", "days": []}'
        sample_request = "Add a beach day"

        formatted = ITINERARY_UPDATE_PROMPT.format(
            current_itinerary=sample_itinerary,
            update_request=sample_request
        )

        assert "Test Trip" in formatted
        assert "Add a beach day" in formatted
        assert "{current_itinerary}" not in formatted
        assert "{update_request}" not in formatted


class TestGenerateItineraryUpdateMethod:
    """Tests for the generate_itinerary_update abstract method on TravelAgent."""

    def test_method_exists_on_travel_agent(self):
        """Test that generate_itinerary_update method is defined on TravelAgent."""
        assert hasattr(TravelAgent, "generate_itinerary_update")
        assert callable(getattr(TravelAgent, "generate_itinerary_update"))

    def test_method_is_abstract(self):
        """Test that generate_itinerary_update is an abstract method."""
        method = getattr(TravelAgent, "generate_itinerary_update")
        # Check if it has the __isabstractmethod__ attribute set to True
        assert getattr(method, "__isabstractmethod__", False), (
            "generate_itinerary_update should be decorated with @abstractmethod"
        )

    def test_method_signature_has_required_parameters(self):
        """Test that the method has the expected signature parameters."""
        sig = inspect.signature(TravelAgent.generate_itinerary_update)
        params = list(sig.parameters.keys())

        # Should have: self, current_itinerary, update_request, language
        assert "self" in params
        assert "current_itinerary" in params
        assert "update_request" in params
        assert "language" in params

    def test_method_language_has_default_value(self):
        """Test that language parameter has a default value."""
        sig = inspect.signature(TravelAgent.generate_itinerary_update)
        language_param = sig.parameters.get("language")

        assert language_param is not None
        assert language_param.default == "English"

    def test_method_return_type_annotation(self):
        """Test that the method has ItineraryDiff return type annotation."""
        sig = inspect.signature(TravelAgent.generate_itinerary_update)

        # Return annotation should be ItineraryDiff
        assert sig.return_annotation == ItineraryDiff

    def test_method_current_itinerary_type_annotation(self):
        """Test that current_itinerary parameter has Itinerary type annotation."""
        sig = inspect.signature(TravelAgent.generate_itinerary_update)
        current_itinerary_param = sig.parameters.get("current_itinerary")

        assert current_itinerary_param is not None
        assert current_itinerary_param.annotation == Itinerary

    def test_method_update_request_type_annotation(self):
        """Test that update_request parameter has str type annotation."""
        sig = inspect.signature(TravelAgent.generate_itinerary_update)
        update_request_param = sig.parameters.get("update_request")

        assert update_request_param is not None
        assert update_request_param.annotation == str
