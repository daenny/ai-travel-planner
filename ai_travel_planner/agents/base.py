from abc import ABC, abstractmethod
from datetime import datetime
import json
import re
from pathlib import Path
from typing import Generator, TYPE_CHECKING

from ai_travel_planner.models import ChatMessage, Itinerary, ItineraryMetadata, DayPlan

if TYPE_CHECKING:
    from ai_travel_planner.models.destination import TripDestinations

# Debug output directory
DEBUG_DIR = Path("debug")
DEBUG_DIR.mkdir(exist_ok=True)


def extract_json_from_response(response: str) -> str:
    """
    Extract JSON from AI response, handling various markdown formats.

    Handles:
    - ```json ... ```
    - ``` ... ```
    - Raw JSON
    - JSON with leading/trailing text
    """
    text = response.strip()

    # Try to find JSON in markdown code blocks
    # Pattern: ```json ... ``` or ``` ... ```
    code_block_pattern = r'```(?:json)?\s*([\s\S]*?)```'
    matches = re.findall(code_block_pattern, text)
    if matches:
        # Use the first (and usually only) code block
        text = matches[0].strip()

    # If still not valid JSON, try to find JSON object boundaries
    if not text.startswith('{'):
        # Find first { and last }
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            text = text[start:end + 1]

    return text


def repair_json(text: str) -> str:
    """
    Attempt to repair common JSON errors from AI responses.

    Handles:
    - Missing quotes on keys at start of lines (e.g., tips": instead of "tips":)
    - Trailing commas before closing brackets
    """
    lines = text.split('\n')
    repaired_lines = []

    for line in lines:
        # Fix missing opening quotes on keys at start of line (after whitespace)
        # Pattern: line starts with whitespace, then unquoted word followed by ":
        # Only match if the key is followed by ": (with closing quote present but opening missing)
        repaired = re.sub(r'^(\s*)([a-zA-Z_][a-zA-Z0-9_]*)(":\s)', r'\1"\2\3', line)
        repaired_lines.append(repaired)

    text = '\n'.join(repaired_lines)

    # Remove trailing commas before ] or }
    text = re.sub(r',(\s*[}\]])', r'\1', text)

    return text


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
{language_instruction}"""

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


def build_language_instruction(language: str) -> str:
    """Build language instruction for the system prompt."""
    if language.lower() == "english":
        return ""
    return f"""
IMPORTANT: Generate ALL content in {language}. This includes activity names, descriptions, tips, day summaries, and packing list items. Keep proper names (places, restaurants) in their original form."""


# Shared itinerary JSON prompt for all agents
ITINERARY_JSON_PROMPT = """Based on the conversation and requirements, generate a complete travel itinerary in JSON format.

The JSON should follow this exact structure:
{
    "title": "Trip title",
    "description": "Brief description",
    "start_date": "YYYY-MM-DD or null",
    "end_date": "YYYY-MM-DD or null",
    "travelers": 4,
    "days": [
        {
            "day_number": 1,
            "date": "YYYY-MM-DD or null",
            "title": "Day title",
            "location": "City/Area name",
            "summary": "Brief summary of the day",
            "image_queries": ["specific evocative search query 1", "specific search query 2"],
            "activities": [
                {
                    "name": "Activity name",
                    "description": "A detailed paragraph (3-5 sentences) describing the activity, what visitors will experience, why it's special, and practical tips. Include sensory details and insider knowledge to bring the experience to life.",
                    "location": "Specific location",
                    "activity_type": "sightseeing|adventure|dining|transport|accommodation|relaxation|wildlife|cultural|shopping",
                    "start_time": "HH:MM or null",
                    "end_time": "HH:MM or null",
                    "cost_estimate": "$XX or null",
                    "booking_required": true/false,
                    "booking_link": "URL or null",
                    "tips": [{"title": "Tip title", "content": "Tip content", "category": "general"}]
                }
            ],
            "tips": [{"title": "Day tip", "content": "Content", "category": "general"}],
            "weather_note": "Expected weather or null"
        }
    ],
    "general_tips": [{"title": "General tip", "content": "Content", "category": "packing|health|safety|money|culture"}],
    "packing_list": ["Item 1", "Item 2"],
    "budget_estimate": "Total estimate or null",
    "emergency_contacts": {"Police": "999", "Ambulance": "999"}
}

IMPORTANT GUIDELINES:

1. Activity descriptions MUST be detailed paragraphs (3-5 sentences each):
   - Describe what visitors will experience and see
   - Explain why the activity is special or memorable
   - Include practical tips (best time to visit, what to bring)
   - Add sensory details and local insights

   BAD: "Visit the temple"
   GOOD: "Explore the ancient Tanah Lot temple perched dramatically on a rocky outcrop, with waves crashing against its base during high tide. Arrive in the late afternoon to witness the spectacular sunset that paints the sky in shades of orange and purple behind the temple silhouette. The temple grounds offer several viewing platforms and local vendors sell offerings and refreshments. During low tide, you can walk across to the base of the temple rock, but the inner sanctum is only open to worshippers."

2. image_queries should contain 2-3 specific, evocative search queries for finding relevant photos:
   - Use location-specific terms (e.g., "golden sunset Tanah Lot Bali" not just "sunset")
   - Include distinctive visual elements (e.g., "orangutan mother baby Sepilok" not just "orangutan")
   - Reference specific landmarks, activities, or atmospheric conditions

   BAD: ["beach", "temple", "food"]
   GOOD: ["Tanah Lot temple sunset silhouette", "Balinese cliff temple ocean waves", "traditional offerings Tanah Lot"]

Return ONLY the JSON, no other text. Make it comprehensive based on all discussed plans."""

# Prompt for generating trip metadata (title, tips, packing list) without days
METADATA_JSON_PROMPT = """Based on the conversation and requirements, generate trip metadata (WITHOUT day plans) in JSON format.

The JSON should follow this exact structure:
{
    "title": "Trip title",
    "description": "Brief description of the trip",
    "total_days": 7,
    "start_date": "YYYY-MM-DD or null",
    "end_date": "YYYY-MM-DD or null",
    "travelers": 4,
    "general_tips": [{"title": "General tip", "content": "Content", "category": "packing|health|safety|money|culture"}],
    "packing_list": ["Item 1", "Item 2", "Item 3"],
    "budget_estimate": "Total estimate or null",
    "emergency_contacts": {"Police": "emergency number", "Ambulance": "emergency number", "Embassy": "number if applicable"}
}

IMPORTANT:
- **total_days**: Determine the appropriate number of days based on the conversation. Consider:
  - Explicit mentions of trip duration (e.g., "7-day trip", "a week")
  - The number of destinations and activities discussed
  - Realistic time needed for the planned experiences
  - If unclear, choose a reasonable duration (5-7 days for a single destination, more for multi-destination)
- Generate ONLY the metadata, NOT the day-by-day itinerary
- The packing list should be comprehensive for the trip destination and activities
- General tips should cover health, safety, money, and cultural considerations
- Emergency contacts should include local emergency numbers for the destination

Return ONLY the JSON, no other text."""

# Prompt template for generating a block of days
DAY_BLOCK_PROMPT = """You are generating days {start_day} to {end_day} of a {total_days}-day trip.

Trip Overview:
- Title: {title}
- Description: {description}
- Total days: {total_days}

{previous_days_context}

Generate ONLY days {start_day} to {end_day} in JSON format. Follow this structure:
{{
    "days": [
        {{
            "day_number": {start_day},
            "date": "YYYY-MM-DD or null",
            "title": "Day title",
            "location": "City/Area name",
            "summary": "Brief summary of the day",
            "image_queries": ["specific evocative search query 1", "specific search query 2"],
            "activities": [
                {{
                    "name": "Activity name",
                    "description": "A detailed paragraph (3-5 sentences) describing the activity, what visitors will experience, why it's special, and practical tips. Include sensory details and insider knowledge to bring the experience to life.",
                    "location": "Specific location",
                    "activity_type": "sightseeing|adventure|dining|transport|accommodation|relaxation|wildlife|cultural|shopping",
                    "start_time": "HH:MM or null",
                    "end_time": "HH:MM or null",
                    "cost_estimate": "$XX or null",
                    "booking_required": true/false,
                    "booking_link": "URL or null",
                    "tips": [{{"title": "Tip title", "content": "Tip content", "category": "general"}}]
                }}
            ],
            "tips": [{{"title": "Day tip", "content": "Content", "category": "general"}}],
            "weather_note": "Expected weather or null"
        }}
    ]
}}

IMPORTANT GUIDELINES:

1. Activity descriptions MUST be detailed paragraphs (3-5 sentences each):
   - Describe what visitors will experience and see
   - Explain why the activity is special or memorable
   - Include practical tips (best time to visit, what to bring)
   - Add sensory details and local insights

2. image_queries should contain 2-3 specific, evocative search queries for finding relevant photos:
   - Use location-specific terms (e.g., "golden sunset Tanah Lot Bali" not just "sunset")
   - Include distinctive visual elements

3. Ensure continuity with previous days:
   - Don't repeat activities or locations unless the user requested it
   - Build a logical flow (e.g., if they visited the north yesterday, explore nearby areas today)
   - Reference previous experiences where appropriate

Return ONLY the JSON with the days array, no other text."""


class TravelAgent(ABC):
    """Abstract base class for travel planning agents."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._destinations: "TripDestinations | None" = None
        self._language: str = "English"
        self._update_system_prompt()

    def set_destinations(self, destinations: "TripDestinations") -> None:
        """Update the agent's destination context."""
        self._destinations = destinations
        self._update_system_prompt()

    def set_language(self, language: str) -> None:
        """Update the agent's language setting."""
        self._language = language
        self._update_system_prompt()

    def _update_system_prompt(self) -> None:
        """Rebuild system prompt based on current destinations and language."""
        expertise = build_destination_expertise(self._destinations)
        language_instruction = build_language_instruction(self._language)
        self.system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            destination_expertise=expertise,
            language_instruction=language_instruction
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
        self, requirements: str, current_itinerary: Itinerary | None = None, language: str = "English"
    ) -> Itinerary:
        """
        Generate or update an itinerary based on requirements.

        Args:
            requirements: Description of what the user wants
            current_itinerary: Existing itinerary to update (if any)
            language: Language for generated content

        Returns:
            Updated Itinerary object
        """
        pass

    @abstractmethod
    def generate_itinerary_metadata(
        self, requirements: str, language: str = "English"
    ) -> ItineraryMetadata:
        """
        Generate trip metadata without day plans.

        The AI determines the appropriate total_days based on the requirements.

        Args:
            requirements: Description of what the user wants
            language: Language for generated content

        Returns:
            ItineraryMetadata object with title, total_days, tips, packing list, etc.
        """
        pass

    @abstractmethod
    def generate_day_block(
        self,
        requirements: str,
        metadata: ItineraryMetadata,
        start_day: int,
        end_day: int,
        total_days: int,
        previous_days: list[DayPlan],
        language: str = "English",
    ) -> list[DayPlan]:
        """
        Generate a block of days (e.g., days 1-3).

        Args:
            requirements: Original trip requirements
            metadata: Trip metadata (title, description, etc.)
            start_day: First day number to generate (1-indexed)
            end_day: Last day number to generate (inclusive)
            total_days: Total days in the trip
            previous_days: Already-generated days for context
            language: Language for generated content

        Returns:
            List of DayPlan objects for the requested range
        """
        pass

    def calculate_day_blocks(self, total_days: int, block_size: int = 3) -> list[tuple[int, int]]:
        """
        Calculate day ranges for iterative generation.

        Args:
            total_days: Total number of days in the trip
            block_size: Number of days per block

        Returns:
            List of (start_day, end_day) tuples, e.g., [(1, 3), (4, 6), (7, 7)] for 7 days
        """
        blocks = []
        for start in range(1, total_days + 1, block_size):
            end = min(start + block_size - 1, total_days)
            blocks.append((start, end))
        return blocks

    def _build_previous_days_context(self, previous_days: list[DayPlan]) -> str:
        """Build a context string summarizing previous days for continuity."""
        if not previous_days:
            return "This is the first block of days - no previous days to reference."

        lines = ["Previously generated days (for context and continuity):"]
        for day in previous_days:
            activities_summary = ", ".join(a.name for a in day.activities[:3])
            if len(day.activities) > 3:
                activities_summary += f" (+{len(day.activities) - 3} more)"
            lines.append(f"- Day {day.day_number} ({day.location}): {day.title} - {activities_summary}")
        lines.append("")
        lines.append("Ensure the new days build naturally on these experiences without repeating activities.")
        return "\n".join(lines)

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
