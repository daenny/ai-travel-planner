from abc import ABC, abstractmethod
from datetime import datetime
import json
import sys
from pathlib import Path
from typing import Generator, TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.models import ChatMessage, Itinerary

if TYPE_CHECKING:
    from src.models.destination import TripDestinations

# Debug output directory
DEBUG_DIR = Path("debug")
DEBUG_DIR.mkdir(exist_ok=True)


# Template-based system prompt - destination-agnostic
SYSTEM_PROMPT_TEMPLATE = """You are an expert travel planner specializing in family trips.
You help families plan memorable, safe, and enriching travel experiences.

{destination_expertise}

When helping plan a trip:
1. Ask about travel dates, number of travelers (adults/children ages)
2. Understand interests (wildlife, beaches, adventure, culture)
3. Consider budget constraints
4. Suggest day-by-day itineraries with specific activities
5. Provide practical tips (what to pack, vaccinations, etc.)
6. Include restaurant and accommodation recommendations

Always be helpful, specific, and consider family-friendly options.
Format your responses clearly with headers and bullet points when listing activities or tips.

When asked to create or update the itinerary, structure your response to include:
- Day number and location
- Morning, afternoon, and evening activities
- Estimated costs where relevant
- Tips specific to each activity or location
"""

# Default expertise when no destination is set
DEFAULT_EXPERTISE = """Your expertise includes:
- Global destination knowledge
- Family-friendly activities and accommodations
- Local cuisine and dining recommendations
- Weather patterns and best times to visit
- Budget planning and cost estimates
- Safety tips and health precautions"""


def build_destination_expertise(destinations: "TripDestinations") -> str:
    """Build expertise section based on detected destinations."""
    if not destinations or not destinations.primary:
        return DEFAULT_EXPERTISE

    dest = destinations.primary
    lines = [f"Your expertise includes planning trips to {dest.name}:"]

    if dest.key_attractions:
        lines.append(f"- Key attractions: {', '.join(dest.key_attractions[:5])}")
    if dest.local_cuisine:
        lines.append(f"- Local cuisine: {dest.local_cuisine}")
    if dest.best_time_to_visit:
        lines.append(f"- Best time to visit: {dest.best_time_to_visit}")

    lines.extend(
        [
            "- Family-friendly activities and accommodations",
            "- Local customs and cultural considerations",
            "- Budget planning and cost estimates",
            "- Safety tips and health precautions",
        ]
    )

    if destinations.secondary:
        secondary_names = [d.name for d in destinations.secondary[:3]]
        lines.append(f"- Also familiar with: {', '.join(secondary_names)}")

    return "\n".join(lines)


class TravelAgent(ABC):
    """Abstract base class for travel planning agents."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._destinations: "TripDestinations | None" = None
        self._update_system_prompt()

    def set_destinations(self, destinations: "TripDestinations") -> None:
        """Update the agent's destination context."""
        self._destinations = destinations
        self._update_system_prompt()

    def _update_system_prompt(self) -> None:
        """Rebuild system prompt based on current destinations."""
        expertise = build_destination_expertise(self._destinations)
        self.system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            destination_expertise=expertise
        )

    def save_debug_response(self, response: str, prefix: str = "itinerary") -> Path:
        """
        Save raw AI response for debugging.

        Args:
            response: The raw response string from the AI
            prefix: Prefix for the filename

        Returns:
            Path to the saved debug file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{self.name.lower()}_{timestamp}.json"
        filepath = DEBUG_DIR / filename

        # Try to pretty-print if it's valid JSON
        try:
            # Extract JSON from markdown code blocks if present
            json_str = response.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            parsed = json.loads(json_str.strip())
            content = json.dumps(parsed, indent=2)
        except (json.JSONDecodeError, IndexError):
            # Save as-is if not valid JSON
            content = response

        filepath.write_text(content)
        return filepath

    @abstractmethod
    def chat(
        self, message: str, history: list[ChatMessage]
    ) -> Generator[str, None, None]:
        """
        Send a message and get a streaming response.

        Args:
            message: User's message
            history: Previous chat messages

        Yields:
            Chunks of the response as they arrive
        """
        pass

    @abstractmethod
    def generate_itinerary_json(
        self, requirements: str, current_itinerary: Itinerary | None = None
    ) -> Itinerary:
        """
        Generate or update an itinerary based on requirements.

        Args:
            requirements: Description of what the user wants
            current_itinerary: Existing itinerary to update (if any)

        Returns:
            Updated Itinerary object
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the display name of this agent."""
        pass

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Return the model ID being used."""
        pass
