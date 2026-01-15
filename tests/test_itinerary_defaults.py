"""Tests for Itinerary default values."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import Itinerary, PlannerSession


class TestItineraryDefaults:
    """Tests for Itinerary default values."""

    def test_default_title_is_generic(self):
        """Test that default title is generic, not Borneo-specific."""
        itinerary = Itinerary()

        # Should not contain Borneo
        assert "Borneo" not in itinerary.title
        assert "Malaysia" not in itinerary.title

        # Should be a reasonable generic title
        assert itinerary.title  # Not empty
        assert len(itinerary.title) > 0

    def test_default_title_value(self):
        """Test the specific default title value."""
        itinerary = Itinerary()
        assert itinerary.title == "My Travel Adventure"

    def test_default_travelers(self):
        """Test default number of travelers."""
        itinerary = Itinerary()
        assert itinerary.travelers == 4

    def test_default_days_empty(self):
        """Test that days list is empty by default."""
        itinerary = Itinerary()
        assert itinerary.days == []

    def test_itinerary_in_session(self):
        """Test that itinerary in session has correct defaults."""
        session = PlannerSession()
        assert session.itinerary.title == "My Travel Adventure"
        assert "Borneo" not in session.itinerary.title


class TestNoHardcodedDestinations:
    """Tests to ensure no hardcoded destinations in defaults."""

    def test_itinerary_model_no_borneo(self):
        """Test Itinerary model doesn't have Borneo references."""
        itinerary = Itinerary()

        # Check all string fields for Borneo references
        assert "Borneo" not in itinerary.title
        assert "Borneo" not in itinerary.description
        assert "Malaysia" not in itinerary.title
        assert "Malaysia" not in itinerary.description

    def test_session_model_no_borneo(self):
        """Test PlannerSession model doesn't have Borneo references."""
        session = PlannerSession()

        # The session should not contain any Borneo-specific defaults
        json_str = session.model_dump_json()
        assert "Borneo" not in json_str
        assert "Sabah" not in json_str
        assert "Sarawak" not in json_str
