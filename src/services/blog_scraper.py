import json
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import httpx
from bs4 import BeautifulSoup

if TYPE_CHECKING:
    from src.agents.base import TravelAgent


@dataclass
class BlogContent:
    """Extracted content from a travel blog."""

    url: str
    title: str
    summary: str
    tips: list[str]
    highlights: list[str]
    images: list[str]
    raw_text: str = ""  # Store raw text for AI processing

    def to_context_string(self) -> str:
        """Convert blog content to a string for AI context."""
        parts = [f"## Blog: {self.title}", f"Source: {self.url}", ""]

        if self.summary:
            parts.append(f"**Summary:** {self.summary}")
            parts.append("")

        if self.tips:
            parts.append("**Tips from this blog:**")
            for tip in self.tips:
                parts.append(f"- {tip}")
            parts.append("")

        if self.highlights:
            parts.append("**Highlights mentioned:**")
            for highlight in self.highlights:
                parts.append(f"- {highlight}")

        return "\n".join(parts)


def build_blog_extraction_prompt(destination: str | None = None) -> str:
    """Build blog extraction prompt, optionally destination-specific."""
    dest_context = ""
    if destination:
        dest_context = f" to {destination}"

    return f"""Analyze this travel blog content and extract useful information for planning a trip{dest_context}.

Return a JSON object with this exact structure:
{{
    "summary": "A 2-3 sentence summary of what this blog post is about",
    "tips": ["tip 1", "tip 2", ...],
    "highlights": ["place or activity 1", "place or activity 2", ...],
    "practical_info": {{
        "budget_mentions": "any budget/cost information mentioned",
        "best_time": "best time to visit if mentioned",
        "warnings": "any warnings or things to avoid"
    }}
}}

Focus on extracting:
- Practical travel tips (what to bring, what to book ahead, etc.)
- Must-see places and activities
- Local food recommendations
- Transportation tips
- Accommodation suggestions
- Safety/health advice
- Budget information

Blog content:
"""


# Default prompt for backward compatibility
BLOG_EXTRACTION_PROMPT = build_blog_extraction_prompt()


class BlogScraper:
    """Service for extracting useful content from travel blogs."""

    def __init__(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )
        }

    def scrape_blog(self, url: str) -> BlogContent | None:
        """
        Scrape content from a travel blog URL.

        Args:
            url: Blog post URL

        Returns:
            BlogContent with extracted information or None if failed
        """
        try:
            with httpx.Client() as client:
                response = client.get(
                    url,
                    headers=self.headers,
                    timeout=15.0,
                    follow_redirects=True,
                )
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()

            title = self._extract_title(soup)
            summary = self._extract_summary(soup)
            tips = self._extract_tips(soup)
            highlights = self._extract_highlights(soup)
            images = self._extract_images(soup, url)
            raw_text = self._extract_raw_text(soup)

            return BlogContent(
                url=url,
                title=title,
                summary=summary,
                tips=tips,
                highlights=highlights,
                images=images,
                raw_text=raw_text,
            )
        except Exception:
            return None

    def _extract_raw_text(self, soup: BeautifulSoup) -> str:
        """Extract clean text content from the blog for AI processing."""
        # Get main content area if possible
        main_content = soup.find("article") or soup.find("main") or soup.find("body")

        if main_content:
            text = main_content.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)

        # Clean up excessive whitespace
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        text = "\n".join(lines)

        # Limit to ~8000 chars for AI processing
        if len(text) > 8000:
            text = text[:8000] + "..."

        return text

    def scrape_with_ai(
        self, url: str, agent: "TravelAgent", destination: str | None = None
    ) -> BlogContent | None:
        """
        Scrape blog and use AI agent to extract tips and summarize.

        Args:
            url: Blog post URL
            agent: AI agent to use for extraction
            destination: Optional destination for context-aware extraction

        Returns:
            BlogContent with AI-extracted information
        """
        # First do basic scraping
        basic_content = self.scrape_blog(url)
        if not basic_content or not basic_content.raw_text:
            return basic_content

        try:
            # Use agent to extract better content
            extraction_prompt = build_blog_extraction_prompt(destination)
            prompt = extraction_prompt + basic_content.raw_text

            # Collect full response (non-streaming)
            full_response = ""
            for chunk in agent.chat(prompt, []):
                full_response += chunk

            # Parse JSON from response
            json_str = full_response.strip()

            # Handle markdown code blocks
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            data = json.loads(json_str.strip())

            # Update content with AI-extracted data
            if data.get("summary"):
                basic_content.summary = data["summary"]

            if data.get("tips"):
                # Combine AI tips with scraped tips, AI first
                ai_tips = data["tips"]
                existing_tips = basic_content.tips
                combined = ai_tips + [t for t in existing_tips if t not in ai_tips]
                basic_content.tips = combined[:15]

            if data.get("highlights"):
                basic_content.highlights = data["highlights"][:15]

            # Add practical info as tips
            practical = data.get("practical_info", {})
            if practical.get("budget_mentions"):
                basic_content.tips.append(f"Budget info: {practical['budget_mentions']}")
            if practical.get("best_time"):
                basic_content.tips.append(f"Best time to visit: {practical['best_time']}")
            if practical.get("warnings"):
                basic_content.tips.append(f"Warning: {practical['warnings']}")

            return basic_content

        except Exception:
            # If AI extraction fails, return basic scraped content
            return basic_content

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract the page title."""
        if soup.title:
            return soup.title.string.strip() if soup.title.string else ""

        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)

        return "Untitled Blog Post"

    def _extract_summary(self, soup: BeautifulSoup) -> str:
        """Extract a summary from meta description or first paragraphs."""
        meta_desc = soup.find("meta", {"name": "description"})
        if meta_desc and meta_desc.get("content"):
            return meta_desc["content"]

        paragraphs = soup.find_all("p")
        text_parts = []
        for p in paragraphs[:5]:
            text = p.get_text(strip=True)
            if len(text) > 50:
                text_parts.append(text)
                if len(" ".join(text_parts)) > 500:
                    break

        return " ".join(text_parts)[:500] + "..." if text_parts else ""

    def _extract_tips(self, soup: BeautifulSoup) -> list[str]:
        """Extract tips from the blog post."""
        tips = []

        tip_patterns = [
            r"tip[s]?:",
            r"pro tip:",
            r"advice:",
            r"recommendation:",
            r"don't forget",
            r"make sure",
            r"remember to",
            r"important:",
            r"note:",
        ]

        for p in soup.find_all(["p", "li"]):
            text = p.get_text(strip=True)
            for pattern in tip_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    if 20 < len(text) < 500:
                        tips.append(text)
                    break

        for heading in soup.find_all(["h2", "h3", "h4"]):
            heading_text = heading.get_text(strip=True).lower()
            if any(word in heading_text for word in ["tip", "advice", "know before"]):
                next_elem = heading.find_next_sibling()
                while next_elem and next_elem.name in ["p", "ul", "ol"]:
                    if next_elem.name in ["ul", "ol"]:
                        for li in next_elem.find_all("li"):
                            text = li.get_text(strip=True)
                            if 20 < len(text) < 500:
                                tips.append(text)
                    else:
                        text = next_elem.get_text(strip=True)
                        if 20 < len(text) < 500:
                            tips.append(text)
                    next_elem = next_elem.find_next_sibling()
                    if next_elem and next_elem.name in ["h2", "h3", "h4"]:
                        break

        return list(set(tips))[:10]

    def _extract_highlights(self, soup: BeautifulSoup) -> list[str]:
        """Extract key highlights/activities from the blog."""
        highlights = []

        for heading in soup.find_all(["h2", "h3"]):
            text = heading.get_text(strip=True)
            if 5 < len(text) < 100:
                highlights.append(text)

        highlight_keywords = [
            "must see",
            "must visit",
            "best",
            "top",
            "highlight",
            "attraction",
            "activity",
            "things to do",
        ]

        for li in soup.find_all("li"):
            text = li.get_text(strip=True)
            text_lower = text.lower()
            if any(kw in text_lower for kw in highlight_keywords):
                if 10 < len(text) < 200:
                    highlights.append(text)

        return list(set(highlights))[:15]

    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        """Extract image URLs from the blog."""
        images = []

        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            if not src:
                continue

            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                from urllib.parse import urlparse

                parsed = urlparse(base_url)
                src = f"{parsed.scheme}://{parsed.netloc}{src}"

            if any(skip in src.lower() for skip in ["logo", "icon", "avatar", "pixel"]):
                continue

            width = img.get("width")
            if width and width.isdigit() and int(width) < 200:
                continue

            images.append(src)

        return images[:10]

    def extract_tips_for_location(self, url: str, location: str) -> list[str]:
        """
        Extract tips relevant to a specific location.

        Args:
            url: Blog URL to scrape
            location: Location to filter tips for

        Returns:
            List of relevant tips
        """
        content = self.scrape_blog(url)
        if not content:
            return []

        location_lower = location.lower()
        relevant_tips = []

        for tip in content.tips:
            if location_lower in tip.lower():
                relevant_tips.append(tip)

        if not relevant_tips:
            return content.tips[:5]

        return relevant_tips
