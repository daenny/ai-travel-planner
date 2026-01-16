from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from ai_travel_planner.models.destination import TripDestinations


class UnsplashService:
    """Service for fetching images from Unsplash API."""

    BASE_URL = "https://api.unsplash.com"

    def __init__(self, access_key: str, cache_dir: Path | str = "images"):
        self.access_key = access_key
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, query: str, size: str = "regular") -> Path:
        """Generate a cache path for a query."""
        hash_key = hashlib.md5(f"{query}_{size}".encode()).hexdigest()[:12]
        safe_query = "".join(c if c.isalnum() else "_" for c in query)[:30]
        return self.cache_dir / f"{safe_query}_{hash_key}.jpg"

    def search_photo(
        self, query: str, orientation: str = "landscape"
    ) -> dict | None:
        """
        Search for a photo on Unsplash.

        Args:
            query: Search query (e.g., "Borneo rainforest")
            orientation: Photo orientation (landscape, portrait, squarish)

        Returns:
            Photo data dict or None if not found
        """
        try:
            with httpx.Client() as client:
                response = client.get(
                    f"{self.BASE_URL}/search/photos",
                    params={
                        "query": query,
                        "orientation": orientation,
                        "per_page": 1,
                    },
                    headers={"Authorization": f"Client-ID {self.access_key}"},
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()

                if data["results"]:
                    return data["results"][0]
                return None
        except Exception:
            return None

    def download_photo(
        self, query: str, size: str = "regular", orientation: str = "landscape"
    ) -> Path | None:
        """
        Search and download a photo, caching locally.

        Args:
            query: Search query
            size: Image size (raw, full, regular, small, thumb)
            orientation: Photo orientation

        Returns:
            Path to cached image or None if failed
        """
        cache_path = self._get_cache_path(query, size)

        if cache_path.exists():
            return cache_path

        photo = self.search_photo(query, orientation)
        if not photo:
            return None

        try:
            image_url = photo["urls"].get(size, photo["urls"]["regular"])

            with httpx.Client() as client:
                response = client.get(image_url, timeout=30.0, follow_redirects=True)
                response.raise_for_status()

                cache_path.write_bytes(response.content)
                return cache_path
        except Exception:
            return None

    def get_photo_for_location(
        self, location: str, activity_type: str | None = None
    ) -> Path | None:
        """
        Get a photo for a specific location, optionally with activity context.

        Args:
            location: Location name (e.g., "Sepilok", "Kuala Lumpur")
            activity_type: Optional activity type for better results

        Returns:
            Path to cached image or None
        """
        if activity_type:
            query = f"{location} {activity_type}"
        else:
            query = f"{location} travel"

        return self.download_photo(query)

    def get_destination_images(
        self, destinations: "TripDestinations"
    ) -> dict[str, Path | None]:
        """
        Fetch images for the detected destinations.

        Args:
            destinations: TripDestinations object with detected destinations

        Returns:
            Dict mapping query to image paths
        """
        queries = []

        for dest in destinations.all_destinations():
            queries.extend(dest.to_image_queries())

        # Add generic travel queries as fallback
        if not queries:
            queries = [
                "travel adventure",
                "vacation landscape",
                "family travel",
            ]

        # Deduplicate while preserving order and limit
        seen = set()
        unique_queries = []
        for q in queries:
            if q.lower() not in seen:
                seen.add(q.lower())
                unique_queries.append(q)
        queries = unique_queries[:10]

        # Use ThreadPoolExecutor for parallel downloads
        results: dict[str, Path | None] = {}
        with ThreadPoolExecutor(max_workers=min(len(queries), 5)) as executor:
            future_to_query = {
                executor.submit(self.download_photo, query): query
                for query in queries
            }
            for future in as_completed(future_to_query):
                query = future_to_query[future]
                try:
                    results[query] = future.result()
                except Exception:
                    results[query] = None

        return results

    def download_photos_for_queries(
        self, queries: list[str], max_images: int = 3
    ) -> list[Path]:
        """
        Download photos for multiple queries in parallel, returning list of cached paths.

        Args:
            queries: List of specific search queries (e.g., AI-generated image queries)
            max_images: Maximum number of images to download (default 3)

        Returns:
            List of paths to downloaded images (may be shorter than max_images if some fail)
        """
        queries_to_fetch = queries[:max_images]
        if not queries_to_fetch:
            return []

        # Use ThreadPoolExecutor for parallel downloads
        results: dict[int, Path | None] = {}
        with ThreadPoolExecutor(max_workers=min(len(queries_to_fetch), 5)) as executor:
            future_to_idx = {
                executor.submit(self.download_photo, query): idx
                for idx, query in enumerate(queries_to_fetch)
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception:
                    results[idx] = None

        # Return in original order, filtering out failures
        return [results[i] for i in sorted(results.keys()) if results[i] is not None]
