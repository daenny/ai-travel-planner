"""Destination models for tracking travel destinations."""

from pydantic import BaseModel, Field


class Destination(BaseModel):
    """Represents a travel destination detected from conversation."""

    name: str  # e.g., "Japan", "Tokyo", "Southeast Asia"
    country: str | None = None  # e.g., "Japan"
    region: str | None = None  # e.g., "Asia"
    confidence: float = 1.0  # 0.0-1.0 confidence score

    # Destination-specific metadata for prompts
    key_attractions: list[str] = Field(default_factory=list)
    local_cuisine: str | None = None
    best_time_to_visit: str | None = None

    def to_image_queries(self) -> list[str]:
        """Generate image search queries for this destination."""
        queries = [
            f"{self.name} travel",
            f"{self.name} landscape",
            f"{self.name} landmarks",
        ]
        if self.country and self.country != self.name:
            queries.append(f"{self.country} scenery")
        return queries


class TripDestinations(BaseModel):
    """Container for tracking multiple destinations in a trip."""

    primary: Destination | None = None
    secondary: list[Destination] = Field(default_factory=list)

    def all_destinations(self) -> list[Destination]:
        """Return all destinations as a flat list."""
        result = []
        if self.primary:
            result.append(self.primary)
        result.extend(self.secondary)
        return result

    def display_name(self) -> str:
        """Return a human-readable name for the trip destination(s)."""
        if not self.primary:
            return "Your Trip"
        if not self.secondary:
            return self.primary.name
        names = [self.primary.name] + [d.name for d in self.secondary[:2]]
        return " & ".join(names)
