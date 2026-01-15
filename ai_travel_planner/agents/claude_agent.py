import json
from typing import Generator

import anthropic

from ai_travel_planner.models import ChatMessage, Itinerary
from .base import TravelAgent


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
            "activities": [
                {
                    "name": "Activity name",
                    "description": "What you'll do",
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

Return ONLY the JSON, no other text. Make it comprehensive based on all discussed plans."""


class ClaudeAgent(TravelAgent):
    """Claude-powered travel planning agent."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        super().__init__(api_key)
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    @property
    def name(self) -> str:
        return "Claude"

    @property
    def model_id(self) -> str:
        return self.model

    def _build_messages(
        self, message: str, history: list[ChatMessage]
    ) -> list[dict]:
        messages = []
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": message})
        return messages

    def chat(
        self, message: str, history: list[ChatMessage]
    ) -> Generator[str, None, None]:
        messages = self._build_messages(message, history)

        with self.client.messages.stream(
            model=self.model,
            max_tokens=4096,
            system=self.system_prompt,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                yield text

    def generate_itinerary_json(
        self, requirements: str, current_itinerary: Itinerary | None = None
    ) -> Itinerary:
        context = ""
        if current_itinerary:
            context = f"\n\nCurrent itinerary to update/expand:\n{current_itinerary.model_dump_json(indent=2)}"

        prompt = f"{requirements}{context}\n\n{ITINERARY_JSON_PROMPT}"

        response = self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            system=self.system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )

        raw_response = response.content[0].text.strip()

        # Save debug output
        debug_path = self.save_debug_response(raw_response)
        print(f"Debug response saved to: {debug_path}")

        json_str = raw_response
        if json_str.startswith("```"):
            json_str = json_str.split("```")[1]
            if json_str.startswith("json"):
                json_str = json_str[4:]
        json_str = json_str.strip()

        data = json.loads(json_str)
        return Itinerary.model_validate(data)
