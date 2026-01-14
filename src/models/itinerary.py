from datetime import date, time
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ActivityType(str, Enum):
    SIGHTSEEING = "sightseeing"
    ADVENTURE = "adventure"
    DINING = "dining"
    TRANSPORT = "transport"
    ACCOMMODATION = "accommodation"
    RELAXATION = "relaxation"
    WILDLIFE = "wildlife"
    CULTURAL = "cultural"
    SHOPPING = "shopping"


class TravelTip(BaseModel):
    title: str
    content: str
    category: str = "general"


class Activity(BaseModel):
    name: str
    description: str
    location: str
    activity_type: ActivityType = ActivityType.SIGHTSEEING
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    cost_estimate: Optional[str] = None
    booking_required: bool = False
    booking_link: Optional[str] = None
    tips: list[TravelTip] = Field(default_factory=list)
    image_url: Optional[str] = None
    image_path: Optional[str] = None


class DayPlan(BaseModel):
    day_number: int
    date: Optional[date] = None
    title: str
    location: str
    summary: str
    activities: list[Activity] = Field(default_factory=list)
    tips: list[TravelTip] = Field(default_factory=list)
    weather_note: Optional[str] = None
    image_url: Optional[str] = None
    image_path: Optional[str] = None


class Itinerary(BaseModel):
    title: str = "Borneo Family Adventure"
    description: str = ""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    travelers: int = 4
    days: list[DayPlan] = Field(default_factory=list)
    general_tips: list[TravelTip] = Field(default_factory=list)
    packing_list: list[str] = Field(default_factory=list)
    budget_estimate: Optional[str] = None
    emergency_contacts: dict[str, str] = Field(default_factory=dict)
    blog_urls: list[str] = Field(default_factory=list)

    def add_day(self, day: DayPlan) -> None:
        self.days.append(day)
        self.days.sort(key=lambda d: d.day_number)

    def get_day(self, day_number: int) -> Optional[DayPlan]:
        for day in self.days:
            if day.day_number == day_number:
                return day
        return None

    def total_days(self) -> int:
        return len(self.days)


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class PlannerSession(BaseModel):
    itinerary: Itinerary = Field(default_factory=Itinerary)
    chat_history: list[ChatMessage] = Field(default_factory=list)
    ai_provider: str = "claude"
