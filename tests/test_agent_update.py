"""Tests for generate_itinerary_update() implementations in all agents."""

import json
from unittest.mock import Mock, MagicMock, patch
import pytest

from ai_travel_planner.models import Itinerary, DayPlan, Activity, ItineraryDiff


# Sample itinerary for testing
def create_sample_itinerary() -> Itinerary:
    """Create a sample itinerary for testing updates."""
    return Itinerary(
        title="Borneo Adventure",
        description="A 5-day wildlife trip",
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
                ],
            ),
        ],
    )


# Sample diff response from AI
SAMPLE_DIFF_RESPONSE = '''{
    "summary": "Added beach activity to Day 1",
    "day_diffs": [
        {
            "operation": "modify",
            "day_number": 1,
            "activity_diffs": [
                {
                    "operation": "add",
                    "position": 2,
                    "activity": {
                        "name": "Beach Sunset",
                        "description": "Watch the sunset at Tanjung Aru Beach",
                        "location": "Tanjung Aru Beach",
                        "activity_type": "relaxation"
                    }
                }
            ]
        }
    ],
    "metadata_changes": []
}'''


class TestClaudeAgentGenerateItineraryUpdate:
    """Tests for ClaudeAgent.generate_itinerary_update()."""

    @patch("ai_travel_planner.agents.claude_agent.anthropic.Anthropic")
    def test_generates_diff_from_update_request(self, mock_anthropic_class):
        """Test that generate_itinerary_update returns an ItineraryDiff."""
        from ai_travel_planner.agents.claude_agent import ClaudeAgent

        # Setup mock
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock()
        mock_response.content = [Mock(text=SAMPLE_DIFF_RESPONSE)]
        mock_client.messages.create.return_value = mock_response

        # Create agent and call method
        agent = ClaudeAgent(api_key="test-key")
        itinerary = create_sample_itinerary()

        diff = agent.generate_itinerary_update(
            current_itinerary=itinerary,
            update_request="Add a beach sunset activity to day 1",
        )

        # Verify result
        assert isinstance(diff, ItineraryDiff)
        assert diff.summary == "Added beach activity to Day 1"
        assert len(diff.day_diffs) == 1
        assert diff.day_diffs[0].day_number == 1

    @patch("ai_travel_planner.agents.claude_agent.anthropic.Anthropic")
    def test_passes_itinerary_to_prompt(self, mock_anthropic_class):
        """Test that the current itinerary is included in the API call."""
        from ai_travel_planner.agents.claude_agent import ClaudeAgent

        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock()
        mock_response.content = [Mock(text=SAMPLE_DIFF_RESPONSE)]
        mock_client.messages.create.return_value = mock_response

        agent = ClaudeAgent(api_key="test-key")
        itinerary = create_sample_itinerary()

        agent.generate_itinerary_update(
            current_itinerary=itinerary,
            update_request="Add beach activity",
        )

        # Verify the API was called with itinerary in the prompt
        call_args = mock_client.messages.create.call_args
        prompt = call_args.kwargs["messages"][0]["content"]

        assert "Borneo Adventure" in prompt
        assert "Add beach activity" in prompt

    @patch("ai_travel_planner.agents.claude_agent.anthropic.Anthropic")
    def test_handles_language_parameter(self, mock_anthropic_class):
        """Test that language parameter affects the prompt."""
        from ai_travel_planner.agents.claude_agent import ClaudeAgent

        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock()
        mock_response.content = [Mock(text=SAMPLE_DIFF_RESPONSE)]
        mock_client.messages.create.return_value = mock_response

        agent = ClaudeAgent(api_key="test-key")
        itinerary = create_sample_itinerary()

        agent.generate_itinerary_update(
            current_itinerary=itinerary,
            update_request="Add beach activity",
            language="German",
        )

        call_args = mock_client.messages.create.call_args
        prompt = call_args.kwargs["messages"][0]["content"]

        assert "German" in prompt

    @patch("ai_travel_planner.agents.claude_agent.anthropic.Anthropic")
    def test_handles_markdown_wrapped_response(self, mock_anthropic_class):
        """Test that markdown-wrapped JSON is handled correctly."""
        from ai_travel_planner.agents.claude_agent import ClaudeAgent

        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        wrapped_response = f"```json\n{SAMPLE_DIFF_RESPONSE}\n```"
        mock_response = Mock()
        mock_response.content = [Mock(text=wrapped_response)]
        mock_client.messages.create.return_value = mock_response

        agent = ClaudeAgent(api_key="test-key")
        itinerary = create_sample_itinerary()

        diff = agent.generate_itinerary_update(
            current_itinerary=itinerary,
            update_request="Add beach activity",
        )

        assert isinstance(diff, ItineraryDiff)
        assert diff.summary == "Added beach activity to Day 1"


class TestOpenAIAgentGenerateItineraryUpdate:
    """Tests for OpenAIAgent.generate_itinerary_update()."""

    @patch("ai_travel_planner.agents.openai_agent.OpenAI")
    def test_generates_diff_from_update_request(self, mock_openai_class):
        """Test that generate_itinerary_update returns an ItineraryDiff."""
        from ai_travel_planner.agents.openai_agent import OpenAIAgent

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content=SAMPLE_DIFF_RESPONSE))]
        mock_client.chat.completions.create.return_value = mock_response

        agent = OpenAIAgent(api_key="test-key")
        itinerary = create_sample_itinerary()

        diff = agent.generate_itinerary_update(
            current_itinerary=itinerary,
            update_request="Add a beach sunset activity to day 1",
        )

        assert isinstance(diff, ItineraryDiff)
        assert diff.summary == "Added beach activity to Day 1"

    @patch("ai_travel_planner.agents.openai_agent.OpenAI")
    def test_passes_itinerary_to_prompt(self, mock_openai_class):
        """Test that the current itinerary is included in the API call."""
        from ai_travel_planner.agents.openai_agent import OpenAIAgent

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content=SAMPLE_DIFF_RESPONSE))]
        mock_client.chat.completions.create.return_value = mock_response

        agent = OpenAIAgent(api_key="test-key")
        itinerary = create_sample_itinerary()

        agent.generate_itinerary_update(
            current_itinerary=itinerary,
            update_request="Add beach activity",
        )

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        user_message = next(m for m in messages if m["role"] == "user")

        assert "Borneo Adventure" in user_message["content"]
        assert "Add beach activity" in user_message["content"]


class TestGeminiAgentGenerateItineraryUpdate:
    """Tests for GeminiAgent.generate_itinerary_update()."""

    @patch("ai_travel_planner.agents.gemini_agent.genai")
    def test_generates_diff_from_update_request(self, mock_genai):
        """Test that generate_itinerary_update returns an ItineraryDiff."""
        from ai_travel_planner.agents.gemini_agent import GeminiAgent

        # Setup mock for genai.Client().models.generate_content()
        mock_client = Mock()
        mock_genai.Client.return_value = mock_client

        mock_response = Mock()
        mock_response.text = SAMPLE_DIFF_RESPONSE
        mock_client.models.generate_content.return_value = mock_response

        agent = GeminiAgent(api_key="test-key")
        itinerary = create_sample_itinerary()

        diff = agent.generate_itinerary_update(
            current_itinerary=itinerary,
            update_request="Add a beach sunset activity to day 1",
        )

        assert isinstance(diff, ItineraryDiff)
        assert diff.summary == "Added beach activity to Day 1"

    @patch("ai_travel_planner.agents.gemini_agent.genai")
    def test_passes_itinerary_to_prompt(self, mock_genai):
        """Test that the current itinerary is included in the API call."""
        from ai_travel_planner.agents.gemini_agent import GeminiAgent

        mock_client = Mock()
        mock_genai.Client.return_value = mock_client

        mock_response = Mock()
        mock_response.text = SAMPLE_DIFF_RESPONSE
        mock_client.models.generate_content.return_value = mock_response

        agent = GeminiAgent(api_key="test-key")
        itinerary = create_sample_itinerary()

        agent.generate_itinerary_update(
            current_itinerary=itinerary,
            update_request="Add beach activity",
        )

        call_args = mock_client.models.generate_content.call_args
        prompt = call_args.kwargs["contents"]

        assert "Borneo Adventure" in prompt
        assert "Add beach activity" in prompt
