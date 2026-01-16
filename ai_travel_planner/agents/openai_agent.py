import json
from typing import Generator

from openai import OpenAI

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


class OpenAIAgent(TravelAgent):
    """OpenAI-powered travel planning agent."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        super().__init__(api_key)
        self.client = OpenAI(api_key=api_key)
        self.model = model

    @property
    def name(self) -> str:
        return "OpenAI"

    @property
    def model_id(self) -> str:
        return self.model

    def _build_messages(
        self, message: str, history: list[ChatMessage]
    ) -> list[dict]:
        messages = [{"role": "system", "content": self.system_prompt}]
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": message})
        return messages

    def chat(
        self, message: str, history: list[ChatMessage]
    ) -> Generator[str, None, None]:
        messages = self._build_messages(message, history)

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=4096,
            stream=True,
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def generate_itinerary_json(
        self, requirements: str, current_itinerary: Itinerary | None = None, language: str = "English"
    ) -> Itinerary:
        context = ""
        if current_itinerary:
            context = f"\n\nCurrent itinerary to update/expand:\n{current_itinerary.model_dump_json(indent=2)}"

        language_note = ""
        if language.lower() != "english":
            language_note = f"\n\nIMPORTANT: Generate all text content in {language}.\n"

        prompt = f"{requirements}{context}{language_note}\n\n{ITINERARY_JSON_PROMPT}"

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ],
            max_tokens=8192,
        )

        raw_response = response.choices[0].message.content.strip()

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
