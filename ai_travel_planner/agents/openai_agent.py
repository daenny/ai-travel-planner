import json
from typing import Generator

from openai import OpenAI
from pydantic import ValidationError

from ai_travel_planner.models import ChatMessage, Itinerary, ItineraryMetadata, ItineraryDiff, DayPlan
from ai_travel_planner.services.itinerary_updater import DiffParseError
from .base import (
    TravelAgent,
    ITINERARY_JSON_PROMPT,
    METADATA_JSON_PROMPT,
    DAY_BLOCK_PROMPT,
    ITINERARY_UPDATE_PROMPT,
    extract_json_from_response,
    repair_json,
)


class OpenAIAgent(TravelAgent):
    """OpenAI-powered travel planning agent."""

    def __init__(self, api_key: str, model: str = "gpt-5.2"):
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

        json_str = extract_json_from_response(raw_response)
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            # Try to repair common JSON errors
            json_str = repair_json(json_str)
            data = json.loads(json_str)
        return Itinerary.model_validate(data)

    def generate_itinerary_metadata(
        self, requirements: str, language: str = "English"
    ) -> ItineraryMetadata:
        language_note = ""
        if language.lower() != "english":
            language_note = f"\n\nIMPORTANT: Generate all text content in {language}.\n"

        prompt = f"""Trip Requirements:
{requirements}
{language_note}
{METADATA_JSON_PROMPT}"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ],
            max_tokens=2048,
        )

        raw_response = response.choices[0].message.content.strip()

        # Save debug output
        debug_path = self.save_debug_response(raw_response, prefix="metadata")
        print(f"Debug metadata response saved to: {debug_path}")

        json_str = extract_json_from_response(raw_response)
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            json_str = repair_json(json_str)
            data = json.loads(json_str)
        return ItineraryMetadata.model_validate(data)

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
        previous_context = self._build_previous_days_context(previous_days)

        language_note = ""
        if language.lower() != "english":
            language_note = f"\n\nIMPORTANT: Generate all text content in {language}.\n"

        prompt = DAY_BLOCK_PROMPT.format(
            start_day=start_day,
            end_day=end_day,
            total_days=total_days,
            title=metadata.title,
            description=metadata.description,
            previous_days_context=previous_context,
        )

        full_prompt = f"""Original Trip Requirements:
{requirements}
{language_note}
{prompt}"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": full_prompt},
            ],
            max_tokens=4096,
        )

        raw_response = response.choices[0].message.content.strip()

        # Save debug output
        debug_path = self.save_debug_response(raw_response, prefix=f"days_{start_day}_{end_day}")
        print(f"Debug day block response saved to: {debug_path}")

        json_str = extract_json_from_response(raw_response)
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            json_str = repair_json(json_str)
            data = json.loads(json_str)

        # Handle both {"days": [...]} and direct [...] formats
        if isinstance(data, list):
            days_data = data
        else:
            days_data = data.get("days", [])

        return [DayPlan.model_validate(d) for d in days_data]

    def generate_itinerary_update(
        self,
        current_itinerary: Itinerary,
        update_request: str,
        language: str = "English",
    ) -> ItineraryDiff:
        itinerary_json = current_itinerary.model_dump_json(indent=2)

        language_note = ""
        if language.lower() != "english":
            language_note = f"\n\nIMPORTANT: Generate all text content in {language}.\n"

        prompt = ITINERARY_UPDATE_PROMPT.format(
            current_itinerary=itinerary_json,
            update_request=update_request,
        )

        full_prompt = f"{prompt}{language_note}"

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": full_prompt},
            ],
            max_tokens=4096,
        )

        raw_response = response.choices[0].message.content.strip()

        # Save debug output
        debug_path = self.save_debug_response(raw_response, prefix="update_diff")
        print(f"Debug update diff response saved to: {debug_path}")

        try:
            json_str = extract_json_from_response(raw_response)
        except ValueError as e:
            raise DiffParseError(
                "The AI response did not contain valid JSON. Please try again.",
                raw_response=raw_response,
                cause=e,
            )

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            # Try to repair common JSON errors
            try:
                json_str = repair_json(json_str)
                data = json.loads(json_str)
            except json.JSONDecodeError:
                raise DiffParseError(
                    "The AI response contained malformed JSON. Please try rephrasing your request.",
                    raw_response=raw_response,
                    cause=e,
                )

        try:
            return ItineraryDiff.model_validate(data)
        except ValidationError as e:
            # Extract user-friendly error message from Pydantic
            error_details = []
            for error in e.errors():
                loc = " -> ".join(str(x) for x in error["loc"])
                error_details.append(f"{loc}: {error['msg']}")
            raise DiffParseError(
                f"The AI generated an invalid update structure: {'; '.join(error_details[:3])}",
                raw_response=raw_response,
                cause=e,
            )
