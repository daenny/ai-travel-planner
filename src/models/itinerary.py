from datetime import date as DateType, time as TimeType, datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


def parse_date(v) -> DateType | None:
    """Parse various date formats to date object."""
    if v is None or v == "null" or v == "":
        return None
    if isinstance(v, DateType):
        return v
    if isinstance(v, str):
        try:
            return datetime.strptime(v, "%Y-%m-%d").date()
        except ValueError:
            pass
        try:
            return datetime.fromisoformat(v).date()
        except ValueError:
            pass
    return None


def parse_time(v) -> TimeType | None:
    """Parse various time formats to time object."""
    if v is None or v == "null" or v == "":
        return None
    if isinstance(v, TimeType):
        return v
    if isinstance(v, str):
        # Try common formats
        for fmt in ["%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M%p"]:
            try:
                return datetime.strptime(v, fmt).time()
            except ValueError:
                continue
    return None


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
    NATURE = "nature"
    BEACH = "beach"
    FOOD = "food"
    OTHER = "other"


# Map common AI-generated variations to valid enum values
ACTIVITY_TYPE_ALIASES = {
    "culture": "cultural",
    "food": "dining",
    "restaurant": "dining",
    "eating": "dining",
    "travel": "transport",
    "flight": "transport",
    "bus": "transport",
    "train": "transport",
    "taxi": "transport",
    "hotel": "accommodation",
    "stay": "accommodation",
    "lodge": "accommodation",
    "hostel": "accommodation",
    "rest": "relaxation",
    "spa": "relaxation",
    "beach": "relaxation",
    "hike": "adventure",
    "hiking": "adventure",
    "trek": "adventure",
    "trekking": "adventure",
    "tour": "sightseeing",
    "visit": "sightseeing",
    "explore": "sightseeing",
    "museum": "cultural",
    "temple": "cultural",
    "market": "shopping",
    "animals": "wildlife",
    "safari": "wildlife",
    "jungle": "wildlife",
    "rainforest": "wildlife",
    "nature": "wildlife",
    "snorkeling": "adventure",
    "diving": "adventure",
    "water": "adventure",
}


class TravelTip(BaseModel):
    title: str
    content: str
    category: str = "general"


class Activity(BaseModel):
    name: str
    description: str
    location: str
    activity_type: ActivityType = ActivityType.SIGHTSEEING
    start_time: TimeType | None = None
    end_time: TimeType | None = None
    cost_estimate: Optional[str] = None
    booking_required: bool = False
    booking_link: Optional[str] = None
    tips: list[TravelTip] = Field(default_factory=list)
    image_url: Optional[str] = None
    image_path: Optional[str] = None

    @field_validator("activity_type", mode="before")
    @classmethod
    def normalize_activity_type(cls, v):
        """Normalize activity type to handle AI variations."""
        if isinstance(v, ActivityType):
            return v
        if isinstance(v, str):
            v_lower = v.lower().strip()
            # Check aliases first
            if v_lower in ACTIVITY_TYPE_ALIASES:
                v_lower = ACTIVITY_TYPE_ALIASES[v_lower]
            # Try to match enum
            try:
                return ActivityType(v_lower)
            except ValueError:
                # Default to sightseeing for unknown types
                return ActivityType.SIGHTSEEING
        return v

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def parse_time_fields(cls, v):
        """Parse time strings to time objects."""
        return parse_time(v)


class DayPlan(BaseModel):
    day_number: int
    date: DateType | None = None
    title: str
    location: str
    summary: str
    activities: list[Activity] = Field(default_factory=list)
    tips: list[TravelTip] = Field(default_factory=list)
    weather_note: Optional[str] = None
    image_url: Optional[str] = None
    image_path: Optional[str] = None

    @field_validator("date", mode="before")
    @classmethod
    def parse_date_field(cls, v):
        """Parse date strings to date objects."""
        return parse_date(v)


class Itinerary(BaseModel):
    title: str = "Borneo Family Adventure"
    description: str = ""
    start_date: DateType | None = None
    end_date: DateType | None = None
    travelers: int = 4
    days: list[DayPlan] = Field(default_factory=list)
    general_tips: list[TravelTip] = Field(default_factory=list)
    packing_list: list[str] = Field(default_factory=list)
    budget_estimate: Optional[str] = None
    emergency_contacts: dict[str, str] = Field(default_factory=dict)
    blog_urls: list[str] = Field(default_factory=list)

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def parse_date_fields(cls, v):
        """Parse date strings to date objects."""
        return parse_date(v)

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


class SavedBlogContent(BaseModel):
    """Blog content model for persistence (mirrors BlogContent dataclass)."""
    url: str
    title: str
    summary: str
    tips: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    raw_text: str = ""


class PlannerSession(BaseModel):
    itinerary: Itinerary = Field(default_factory=Itinerary)
    chat_history: list[ChatMessage] = Field(default_factory=list)
    ai_provider: str = "claude"
    blog_content: dict[str, SavedBlogContent] = Field(default_factory=dict)
