"""Tests for dynamic system prompt generation."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.base import (
    SYSTEM_PROMPT_TEMPLATE,
    DEFAULT_EXPERTISE,
    build_destination_expertise,
)
from src.models.destination import Destination, TripDestinations


class TestBuildDestinationExpertise:
    """Tests for build_destination_expertise function."""

    def test_no_destination(self):
        """Test that default expertise is returned when no destination."""
        result = build_destination_expertise(None)
        assert result == DEFAULT_EXPERTISE

    def test_empty_destinations(self):
        """Test that default expertise is returned for empty TripDestinations."""
        trip = TripDestinations()
        result = build_destination_expertise(trip)
        assert result == DEFAULT_EXPERTISE

    def test_single_destination(self):
        """Test expertise for single destination."""
        trip = TripDestinations(
            primary=Destination(name="Japan", country="Japan", region="Asia")
        )
        result = build_destination_expertise(trip)

        assert "Japan" in result
        assert "Family-friendly" in result
        assert "Local customs" in result
        assert "Budget planning" in result

    def test_destination_with_attractions(self):
        """Test that key attractions are included."""
        trip = TripDestinations(
            primary=Destination(
                name="Tokyo",
                key_attractions=["Tokyo Tower", "Shibuya"],
            )
        )
        result = build_destination_expertise(trip)

        assert "Tokyo" in result
        assert "Tokyo Tower" in result
        assert "Shibuya" in result

    def test_destination_with_cuisine(self):
        """Test that local cuisine is included."""
        trip = TripDestinations(
            primary=Destination(
                name="Italy",
                local_cuisine="Pizza, pasta, gelato",
            )
        )
        result = build_destination_expertise(trip)

        assert "Italy" in result
        assert "Pizza" in result

    def test_destination_with_best_time(self):
        """Test that best time to visit is included."""
        trip = TripDestinations(
            primary=Destination(
                name="Thailand",
                best_time_to_visit="November to February",
            )
        )
        result = build_destination_expertise(trip)

        assert "Thailand" in result
        assert "November to February" in result

    def test_secondary_destinations_mentioned(self):
        """Test that secondary destinations are mentioned."""
        trip = TripDestinations(
            primary=Destination(name="Tokyo"),
            secondary=[
                Destination(name="Kyoto"),
                Destination(name="Osaka"),
            ],
        )
        result = build_destination_expertise(trip)

        assert "Tokyo" in result
        assert "Also familiar with" in result
        assert "Kyoto" in result
        assert "Osaka" in result


class TestSystemPromptTemplate:
    """Tests for the system prompt template."""

    def test_template_has_placeholder(self):
        """Test that template contains destination_expertise placeholder."""
        assert "{destination_expertise}" in SYSTEM_PROMPT_TEMPLATE

    def test_template_can_be_formatted(self):
        """Test that template can be formatted with expertise."""
        result = SYSTEM_PROMPT_TEMPLATE.format(destination_expertise="Test expertise")
        assert "Test expertise" in result
        assert "{destination_expertise}" not in result

    def test_template_contains_planning_instructions(self):
        """Test that template contains planning instructions."""
        assert "travel dates" in SYSTEM_PROMPT_TEMPLATE.lower()
        assert "itinerary" in SYSTEM_PROMPT_TEMPLATE.lower()
        assert "tips" in SYSTEM_PROMPT_TEMPLATE.lower()


class TestDefaultExpertise:
    """Tests for default expertise string."""

    def test_default_expertise_is_generic(self):
        """Test that default expertise doesn't mention specific destinations."""
        # Should not contain Borneo or any specific destination
        assert "Borneo" not in DEFAULT_EXPERTISE
        assert "Malaysia" not in DEFAULT_EXPERTISE
        assert "Kuala Lumpur" not in DEFAULT_EXPERTISE

    def test_default_expertise_covers_general_topics(self):
        """Test that default expertise covers general travel topics."""
        assert "Global" in DEFAULT_EXPERTISE or "destination" in DEFAULT_EXPERTISE.lower()
        assert "Family-friendly" in DEFAULT_EXPERTISE
        assert "Budget" in DEFAULT_EXPERTISE
