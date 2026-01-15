"""Tests for PlannerSession persistence."""

import json

from ai_travel_planner.models import PlannerSession, ChatMessage, Itinerary
from ai_travel_planner.models.destination import Destination, TripDestinations


class TestPlannerSession:
    """Tests for PlannerSession model."""

    def test_session_creation(self):
        """Test basic session creation."""
        session = PlannerSession()
        assert session.itinerary is not None
        assert session.chat_history == []
        assert session.ai_provider == "claude"
        assert session.destinations is not None

    def test_session_with_destinations(self):
        """Test session with destinations."""
        session = PlannerSession(
            destinations=TripDestinations(
                primary=Destination(name="Japan")
            )
        )
        assert session.destinations.primary is not None
        assert session.destinations.primary.name == "Japan"

    def test_session_serialization(self):
        """Test that session can be serialized to JSON."""
        session = PlannerSession(
            chat_history=[
                ChatMessage(role="user", content="Plan a trip to Japan"),
                ChatMessage(role="assistant", content="I'd love to help!"),
            ],
            destinations=TripDestinations(
                primary=Destination(name="Japan", country="Japan")
            ),
        )

        # Serialize to JSON
        json_str = session.model_dump_json()
        data = json.loads(json_str)

        assert data["ai_provider"] == "claude"
        assert len(data["chat_history"]) == 2
        assert data["destinations"]["primary"]["name"] == "Japan"

    def test_session_deserialization(self):
        """Test that session can be deserialized from JSON."""
        json_data = {
            "itinerary": {"title": "My Trip"},
            "chat_history": [
                {"role": "user", "content": "Hello"}
            ],
            "ai_provider": "openai",
            "blog_content": {},
            "destinations": {
                "primary": {"name": "Italy", "country": "Italy"},
                "secondary": [],
            },
        }

        session = PlannerSession.model_validate(json_data)

        assert session.itinerary.title == "My Trip"
        assert len(session.chat_history) == 1
        assert session.ai_provider == "openai"
        assert session.destinations.primary.name == "Italy"

    def test_backward_compatibility_no_destinations(self):
        """Test loading session without destinations field (backward compat)."""
        # Old session format without destinations
        json_data = {
            "itinerary": {"title": "Old Trip"},
            "chat_history": [],
            "ai_provider": "claude",
            "blog_content": {},
        }

        # Should not raise an error, destinations should be default
        session = PlannerSession.model_validate(json_data)

        assert session.itinerary.title == "Old Trip"
        assert session.destinations is not None
        assert session.destinations.primary is None  # Default empty

    def test_destinations_preserved_through_round_trip(self):
        """Test that destinations survive serialization round trip."""
        original = PlannerSession(
            destinations=TripDestinations(
                primary=Destination(
                    name="Tokyo",
                    country="Japan",
                    key_attractions=["Tokyo Tower"],
                ),
                secondary=[Destination(name="Kyoto")],
            )
        )

        # Round trip through JSON
        json_str = original.model_dump_json()
        restored = PlannerSession.model_validate_json(json_str)

        assert restored.destinations.primary.name == "Tokyo"
        assert restored.destinations.primary.country == "Japan"
        assert "Tokyo Tower" in restored.destinations.primary.key_attractions
        assert len(restored.destinations.secondary) == 1
        assert restored.destinations.secondary[0].name == "Kyoto"
