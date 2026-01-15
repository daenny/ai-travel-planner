"""Tests for the Destination model."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.destination import Destination, TripDestinations


class TestDestination:
    """Tests for the Destination model."""

    def test_destination_creation(self):
        """Test basic destination creation."""
        dest = Destination(name="Japan", country="Japan", region="Asia")
        assert dest.name == "Japan"
        assert dest.country == "Japan"
        assert dest.region == "Asia"
        assert dest.confidence == 1.0  # Default value

    def test_destination_with_attractions(self):
        """Test destination with key attractions."""
        dest = Destination(
            name="Tokyo",
            country="Japan",
            region="Asia",
            key_attractions=["Shibuya Crossing", "Tokyo Tower", "Senso-ji Temple"],
        )
        assert len(dest.key_attractions) == 3
        assert "Tokyo Tower" in dest.key_attractions

    def test_to_image_queries(self):
        """Test generating image search queries."""
        dest = Destination(name="Tokyo", country="Japan")
        queries = dest.to_image_queries()

        assert "Tokyo travel" in queries
        assert "Tokyo landscape" in queries
        assert "Tokyo landmarks" in queries
        assert "Japan scenery" in queries

    def test_to_image_queries_same_name_country(self):
        """Test image queries when name and country are the same."""
        dest = Destination(name="Japan", country="Japan")
        queries = dest.to_image_queries()

        # Should not include duplicate "Japan scenery"
        assert queries.count("Japan scenery") <= 1


class TestTripDestinations:
    """Tests for the TripDestinations model."""

    def test_empty_destinations(self):
        """Test empty destinations."""
        trip = TripDestinations()
        assert trip.primary is None
        assert trip.secondary == []
        assert trip.display_name() == "Your Trip"
        assert trip.all_destinations() == []

    def test_single_destination(self):
        """Test with a single primary destination."""
        trip = TripDestinations(primary=Destination(name="Japan"))
        assert trip.display_name() == "Japan"
        assert len(trip.all_destinations()) == 1

    def test_multiple_destinations(self):
        """Test with primary and secondary destinations."""
        trip = TripDestinations(
            primary=Destination(name="Tokyo"),
            secondary=[
                Destination(name="Kyoto"),
                Destination(name="Osaka"),
            ],
        )
        assert trip.display_name() == "Tokyo & Kyoto & Osaka"
        assert len(trip.all_destinations()) == 3

    def test_display_name_limits_secondary(self):
        """Test that display name limits secondary destinations to 2."""
        trip = TripDestinations(
            primary=Destination(name="Tokyo"),
            secondary=[
                Destination(name="Kyoto"),
                Destination(name="Osaka"),
                Destination(name="Hiroshima"),
                Destination(name="Nara"),
            ],
        )
        # Should only show first 2 secondary destinations
        display = trip.display_name()
        assert "Tokyo" in display
        assert "Kyoto" in display
        assert "Osaka" in display
        assert "Hiroshima" not in display

    def test_all_destinations_order(self):
        """Test that all_destinations returns primary first."""
        trip = TripDestinations(
            primary=Destination(name="Tokyo"),
            secondary=[Destination(name="Kyoto")],
        )
        all_dest = trip.all_destinations()
        assert all_dest[0].name == "Tokyo"
        assert all_dest[1].name == "Kyoto"
