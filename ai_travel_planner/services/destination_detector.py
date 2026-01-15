"""Service for detecting travel destinations from conversation."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_travel_planner.agents.base import TravelAgent
    from ai_travel_planner.models import ChatMessage

from ai_travel_planner.models.destination import Destination, TripDestinations


DESTINATION_EXTRACTION_PROMPT = """Analyze this conversation and extract the travel destination(s) being discussed.

Return a JSON object with this structure:
{
    "primary_destination": {
        "name": "Main destination name (city or country)",
        "country": "Country name",
        "region": "Geographic region (e.g., Asia, Europe, Americas)",
        "key_attractions": ["attraction1", "attraction2"],
        "local_cuisine": "Brief description of local food",
        "best_time_to_visit": "Best season/months"
    },
    "secondary_destinations": [
        {"name": "...", "country": "...", "region": "..."}
    ],
    "confidence": 0.0-1.0
}

If no destination is mentioned or clear, return:
{"primary_destination": null, "secondary_destinations": [], "confidence": 0.0}

Conversation:
"""


class DestinationDetector:
    """Service for detecting destinations from conversation."""

    # Common destination patterns
    DESTINATION_PATTERNS = [
        r"(?:trip|travel(?:l?ing)?|go(?:ing)?|visit(?:ing)?|vacation|holiday|journey) to ([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",
        r"(?:trip|travel(?:l?ing)?|go(?:ing)?|visit(?:ing)?|vacation|holiday|journey) in ([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",
        r"(?:plan(?:ning)?|book(?:ing)?) (?:a )?(?:trip|travel|vacation|holiday) to ([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",
        r"(?:want|like|love) to (?:go|visit|travel|see) ([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",
        r"(?:are |we are |we're )?visiting ([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",
    ]

    def extract_from_text(self, text: str) -> list[str]:
        """
        Quick rule-based extraction for fast destination detection.

        Args:
            text: Text to search for destinations

        Returns:
            List of detected destination names
        """
        destinations = []

        for pattern in self.DESTINATION_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            destinations.extend(matches)

        # Also try simpler patterns with capitalized words after common phrases
        simple_patterns = [
            r"trip to (\w+(?:\s+\w+)?)",
            r"visit(?:ing)? (\w+(?:\s+\w+)?)",
            r"travel(?:ing)? to (\w+(?:\s+\w+)?)",
            r"going to (\w+(?:\s+\w+)?)",
            r"vacation in (\w+(?:\s+\w+)?)",
            r"holiday in (\w+(?:\s+\w+)?)",
        ]

        for pattern in simple_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            # Filter out common words that aren't destinations
            filtered = [
                m
                for m in matches
                if m.lower()
                not in {
                    "the",
                    "a",
                    "an",
                    "my",
                    "our",
                    "your",
                    "their",
                    "be",
                    "go",
                    "see",
                    "do",
                    "have",
                    "there",
                    "here",
                    "somewhere",
                    "anywhere",
                }
            ]
            destinations.extend(filtered)

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for dest in destinations:
            dest_lower = dest.lower()
            if dest_lower not in seen:
                seen.add(dest_lower)
                unique.append(dest)

        return unique

    def extract_from_conversation(
        self, chat_history: list["ChatMessage"], agent: "TravelAgent"
    ) -> TripDestinations:
        """
        Extract destinations using AI analysis.

        Args:
            chat_history: List of chat messages to analyze
            agent: Travel agent to use for AI extraction

        Returns:
            TripDestinations with detected primary and secondary destinations
        """
        if not chat_history:
            return TripDestinations()

        # Build conversation text from last 10 messages for efficiency
        conversation = "\n".join(
            f"{msg.role}: {msg.content}" for msg in chat_history[-10:]
        )

        prompt = DESTINATION_EXTRACTION_PROMPT + conversation

        # Use agent to extract
        full_response = ""
        for chunk in agent.chat(prompt, []):
            full_response += chunk

        # Parse JSON response
        try:
            # Handle markdown code blocks
            json_str = full_response.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            data = json.loads(json_str.strip())
            return self._parse_response(data)
        except (json.JSONDecodeError, KeyError, IndexError):
            return TripDestinations()

    def _parse_response(self, data: dict) -> TripDestinations:
        """Parse AI response into TripDestinations model."""
        result = TripDestinations()

        if data.get("primary_destination"):
            pd = data["primary_destination"]
            result.primary = Destination(
                name=pd.get("name", ""),
                country=pd.get("country"),
                region=pd.get("region"),
                key_attractions=pd.get("key_attractions", []),
                local_cuisine=pd.get("local_cuisine"),
                best_time_to_visit=pd.get("best_time_to_visit"),
                confidence=data.get("confidence", 1.0),
            )

        for sd in data.get("secondary_destinations", []):
            result.secondary.append(
                Destination(
                    name=sd.get("name", ""),
                    country=sd.get("country"),
                    region=sd.get("region"),
                    key_attractions=sd.get("key_attractions", []),
                )
            )

        return result
