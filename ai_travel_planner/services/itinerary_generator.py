"""
Iterative itinerary generation service.

Generates itineraries in blocks to provide progress feedback and handle
longer trips more effectively. Supports resuming from partial completion.
"""

from typing import Generator

from ai_travel_planner.agents.base import TravelAgent
from ai_travel_planner.models import Itinerary, ItineraryMetadata, GenerationProgress, DayPlan


def generate_itinerary_iteratively(
    agent: TravelAgent,
    requirements: str,
    language: str = "English",
    block_size: int = 3,
) -> Generator[tuple[GenerationProgress, Itinerary, ItineraryMetadata | None], None, None]:
    """
    Generate an itinerary iteratively, yielding progress after each step.

    This function generates the itinerary in blocks:
    1. First, generates metadata (title, tips, packing list) - AI determines total_days
    2. Then generates days in blocks of `block_size`

    Args:
        agent: The travel agent to use for generation
        requirements: Trip requirements from the conversation
        language: Language for generated content
        block_size: Number of days to generate per block (default 3)

    Yields:
        Tuple of (GenerationProgress, Itinerary, ItineraryMetadata) after each step.
        The metadata is returned for storing in case resume is needed.
    """
    # Initialize progress with placeholder total_days (will be updated after metadata)
    progress = GenerationProgress(
        total_days=0,
        completed_days=0,
        current_block_start=0,
        current_block_end=0,
        status="generating_metadata",
    )

    # Initialize empty itinerary
    itinerary = Itinerary()
    metadata: ItineraryMetadata | None = None

    # Step 1: Generate metadata - AI determines total_days
    try:
        metadata = agent.generate_itinerary_metadata(requirements, language)
        itinerary = Itinerary.from_metadata(metadata)

        # Get total_days from AI-generated metadata
        total_days = max(1, metadata.total_days)
        progress.total_days = total_days
        progress.status = "generating_days"
        yield progress, itinerary, metadata

    except Exception as e:
        progress.status = "error"
        progress.error_message = f"Failed to generate metadata: {str(e)}"
        yield progress, itinerary, None
        return

    # Generate days using shared logic
    yield from _generate_days(
        agent=agent,
        requirements=requirements,
        metadata=metadata,
        itinerary=itinerary,
        progress=progress,
        existing_days=[],
        block_size=block_size,
        language=language,
    )


def resume_itinerary_generation(
    agent: TravelAgent,
    requirements: str,
    metadata: ItineraryMetadata,
    existing_itinerary: Itinerary,
    language: str = "English",
    block_size: int = 3,
) -> Generator[tuple[GenerationProgress, Itinerary, ItineraryMetadata], None, None]:
    """
    Resume itinerary generation from a partial state.

    Args:
        agent: The travel agent to use for generation
        requirements: Original trip requirements
        metadata: Previously generated metadata
        existing_itinerary: Itinerary with already-generated days
        language: Language for generated content
        block_size: Number of days to generate per block

    Yields:
        Tuple of (GenerationProgress, Itinerary, ItineraryMetadata) after each step.
    """
    total_days = max(1, metadata.total_days)
    existing_days = list(existing_itinerary.days)
    completed_days = len(existing_days)

    # Initialize progress from existing state
    progress = GenerationProgress(
        total_days=total_days,
        completed_days=completed_days,
        current_block_start=completed_days + 1,
        current_block_end=0,
        status="generating_days",
    )

    # Start with existing itinerary
    itinerary = existing_itinerary.model_copy(deep=True)

    # Yield initial state
    yield progress, itinerary, metadata

    # Generate remaining days
    yield from _generate_days(
        agent=agent,
        requirements=requirements,
        metadata=metadata,
        itinerary=itinerary,
        progress=progress,
        existing_days=existing_days,
        block_size=block_size,
        language=language,
    )


def _generate_days(
    agent: TravelAgent,
    requirements: str,
    metadata: ItineraryMetadata,
    itinerary: Itinerary,
    progress: GenerationProgress,
    existing_days: list[DayPlan],
    block_size: int,
    language: str,
) -> Generator[tuple[GenerationProgress, Itinerary, ItineraryMetadata], None, None]:
    """
    Internal function to generate days in blocks.

    Shared by both generate_itinerary_iteratively and resume_itinerary_generation.
    """
    total_days = progress.total_days
    all_days = list(existing_days)
    start_from_day = len(all_days) + 1

    # Calculate remaining blocks
    blocks = []
    for start in range(start_from_day, total_days + 1, block_size):
        end = min(start + block_size - 1, total_days)
        blocks.append((start, end))

    if not blocks:
        # Already complete
        progress.status = "complete"
        yield progress, itinerary, metadata
        return

    # Generate each block of days
    for start_day, end_day in blocks:
        progress.current_block_start = start_day
        progress.current_block_end = end_day

        try:
            new_days = agent.generate_day_block(
                requirements=requirements,
                metadata=metadata,
                start_day=start_day,
                end_day=end_day,
                total_days=total_days,
                previous_days=all_days,
                language=language,
            )

            # Add new days to the collection
            all_days.extend(new_days)

            # Update itinerary with all days so far
            itinerary.days = sorted(all_days, key=lambda d: d.day_number)

            # Update progress
            progress.completed_days = len(all_days)

            # Check if complete
            if progress.completed_days >= total_days:
                progress.status = "complete"

            yield progress, itinerary, metadata

        except Exception as e:
            # Mark as partial (can be resumed) rather than just error
            progress.status = "partial" if progress.completed_days > 0 else "error"
            progress.error_message = f"Failed to generate days {start_day}-{end_day}: {str(e)}"
            yield progress, itinerary, metadata
            return

    # Final check - ensure status is complete
    if progress.status not in ("error", "partial"):
        progress.status = "complete"
        yield progress, itinerary, metadata
