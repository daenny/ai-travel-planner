import json
import sys
from pathlib import Path
from typing import Generator

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from google import genai
from google.genai import types

from src.models import ChatMessage, Itinerary
from .base import TravelAgent, SYSTEM_PROMPT


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


class GeminiAgent(TravelAgent):
    """Google Gemini-powered travel planning agent."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        super().__init__(api_key)
        self.client = genai.Client(api_key=api_key)
        self._model_id = model

    @property
    def name(self) -> str:
        return "Gemini"

    @property
    def model_id(self) -> str:
        return self._model_id

    def _build_contents(
        self, message: str, history: list[ChatMessage]
    ) -> list[types.Content]:
        """Build contents list for Gemini API."""
        contents = []
        for msg in history:
            role = "user" if msg.role == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part(text=msg.content)]))
        contents.append(types.Content(role="user", parts=[types.Part(text=message)]))
        return contents

    def chat(
        self, message: str, history: list[ChatMessage]
    ) -> Generator[str, None, None]:
        contents = self._build_contents(message, history)

        response = self.client.models.generate_content_stream(
            model=self._model_id,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=self.system_prompt,
            ),
        )

        for chunk in response:
            if chunk.text:
                yield chunk.text

    def generate_itinerary_json(
        self, requirements: str, current_itinerary: Itinerary | None = None
    ) -> Itinerary:
        context = ""
        if current_itinerary:
            context = f"\n\nCurrent itinerary to update/expand:\n{current_itinerary.model_dump_json(indent=2)}"

        prompt = f"{requirements}{context}\n\n{ITINERARY_JSON_PROMPT}"

        response = self.client.models.generate_content(
            model=self._model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
            ),
        )

        json_str = response.text.strip()
        if json_str.startswith("```"):
            json_str = json_str.split("```")[1]
            if json_str.startswith("json"):
                json_str = json_str[4:]
        json_str = json_str.strip()

        data = json.loads(json_str)
        return Itinerary.model_validate(data)
