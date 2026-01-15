import json
from datetime import date, time
from pathlib import Path

from ai_travel_planner.models import Itinerary, PlannerSession


class JSONStore:
    """Service for saving and loading travel plans as JSON."""

    def __init__(self, plans_dir: Path | str = "plans"):
        self.plans_dir = Path(plans_dir)
        self.plans_dir.mkdir(parents=True, exist_ok=True)

    def _get_plan_path(self, name: str) -> Path:
        """Get the file path for a plan by name."""
        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in name)
        return self.plans_dir / f"{safe_name}.json"

    def save_itinerary(self, itinerary: Itinerary, name: str | None = None) -> Path:
        """
        Save an itinerary to a JSON file.

        Args:
            itinerary: The itinerary to save
            name: Optional custom name (defaults to itinerary title)

        Returns:
            Path to the saved file
        """
        if name is None:
            name = itinerary.title

        path = self._get_plan_path(name)

        data = itinerary.model_dump(mode="json")

        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        return path

    def load_itinerary(self, name: str) -> Itinerary | None:
        """
        Load an itinerary from a JSON file.

        Args:
            name: Name of the plan to load

        Returns:
            Loaded Itinerary or None if not found
        """
        path = self._get_plan_path(name)

        if not path.exists():
            return None

        try:
            with open(path) as f:
                data = json.load(f)
            return Itinerary.model_validate(data)
        except Exception:
            return None

    def save_session(self, session: PlannerSession, name: str) -> Path:
        """
        Save a complete planner session (itinerary + chat history).

        Args:
            session: The session to save
            name: Name for the session

        Returns:
            Path to the saved file
        """
        path = self._get_plan_path(f"session_{name}")

        data = session.model_dump(mode="json")

        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        return path

    def load_session(self, name: str) -> PlannerSession | None:
        """
        Load a planner session.

        Args:
            name: Name of the session to load

        Returns:
            Loaded PlannerSession or None if not found
        """
        path = self._get_plan_path(f"session_{name}")

        if not path.exists():
            return None

        try:
            with open(path) as f:
                data = json.load(f)
            return PlannerSession.model_validate(data)
        except Exception:
            return None

    def list_plans(self) -> list[str]:
        """
        List all saved plans.

        Returns:
            List of plan names (without .json extension)
        """
        plans = []
        for path in self.plans_dir.glob("*.json"):
            if not path.name.startswith("session_"):
                plans.append(path.stem)
        return sorted(plans)

    def list_sessions(self) -> list[str]:
        """
        List all saved sessions.

        Returns:
            List of session names
        """
        sessions = []
        for path in self.plans_dir.glob("session_*.json"):
            name = path.stem.replace("session_", "", 1)
            sessions.append(name)
        return sorted(sessions)

    def delete_plan(self, name: str) -> bool:
        """
        Delete a saved plan.

        Args:
            name: Name of the plan to delete

        Returns:
            True if deleted, False if not found
        """
        path = self._get_plan_path(name)
        if path.exists():
            path.unlink()
            return True
        return False

    def delete_session(self, name: str) -> bool:
        """
        Delete a saved session.

        Args:
            name: Name of the session to delete

        Returns:
            True if deleted, False if not found
        """
        path = self._get_plan_path(f"session_{name}")
        if path.exists():
            path.unlink()
            return True
        return False
