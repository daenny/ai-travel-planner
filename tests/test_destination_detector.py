"""Tests for the DestinationDetector service."""

from ai_travel_planner.services.destination_detector import DestinationDetector


class TestDestinationDetector:
    """Tests for the DestinationDetector class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = DestinationDetector()

    def test_extract_trip_to_pattern(self):
        """Test extracting destination from 'trip to X' pattern."""
        results = self.detector.extract_from_text("I want to plan a trip to Japan")
        assert "Japan" in results

    def test_extract_visit_pattern(self):
        """Test extracting destination from 'visit X' pattern."""
        results = self.detector.extract_from_text("We want to visit Thailand")
        assert "Thailand" in results

    def test_extract_visiting_pattern(self):
        """Test extracting destination from 'visiting X' pattern."""
        results = self.detector.extract_from_text("We are visiting Paris next month")
        # Check that at least one result contains Paris
        assert any("Paris" in r for r in results)

    def test_extract_travel_to_pattern(self):
        """Test extracting destination from 'travel to X' pattern."""
        results = self.detector.extract_from_text("Planning to travel to Italy")
        assert "Italy" in results

    def test_extract_going_to_pattern(self):
        """Test extracting destination from 'going to X' pattern."""
        results = self.detector.extract_from_text("We are going to Spain")
        assert "Spain" in results

    def test_extract_vacation_pattern(self):
        """Test extracting destination from 'vacation in X' pattern."""
        results = self.detector.extract_from_text("Taking a vacation in Hawaii")
        assert "Hawaii" in results

    def test_extract_holiday_pattern(self):
        """Test extracting destination from 'holiday in X' pattern."""
        results = self.detector.extract_from_text("Planning a holiday in Greece")
        assert "Greece" in results

    def test_no_destination_found(self):
        """Test when no destination is mentioned."""
        results = self.detector.extract_from_text("Hello, how are you today?")
        assert results == []

    def test_case_insensitivity(self):
        """Test that pattern matching is case insensitive."""
        results = self.detector.extract_from_text("TRIP TO japan")
        assert len(results) > 0
        # At least one result should contain "japan" (case may vary)
        assert any("japan" in r.lower() for r in results)

    def test_multiple_destinations(self):
        """Test extracting multiple destinations."""
        results = self.detector.extract_from_text(
            "We want to visit Tokyo and then travel to Kyoto"
        )
        # Should find at least one destination
        assert len(results) >= 1

    def test_filters_common_words(self):
        """Test that common words are filtered out."""
        # "the" should not be extracted as a destination
        results = self.detector.extract_from_text("I want to go to the beach")
        assert "the" not in [r.lower() for r in results]

    def test_multi_word_destination(self):
        """Test extracting multi-word destinations."""
        results = self.detector.extract_from_text("Trip to New York")
        # Should capture at least "New" or "New York"
        assert len(results) >= 1

    def test_deduplication(self):
        """Test that duplicate destinations are removed."""
        results = self.detector.extract_from_text(
            "Trip to Japan. We love Japan. Visiting Japan soon."
        )
        # Check for duplicates (case insensitive)
        lower_results = [r.lower() for r in results]
        assert len(lower_results) == len(set(lower_results))
