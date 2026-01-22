# Technology Stack: Travel Planner

## Overview

This document defines the technology choices for the Travel Planner application. Any changes to this stack must be documented here before implementation.

---

## Language & Runtime

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.12+ | Primary programming language |

### Rationale
Python provides excellent support for AI/ML integrations, web frameworks, and rapid prototyping. The 3.12+ requirement ensures access to modern language features and performance improvements.

---

## Package Management & Build

| Technology | Purpose |
|------------|---------|
| Pixi | Dependency management via conda-forge |
| Hatchling | Python build backend |

### Configuration Files
- `pixi.toml` - Pixi workspace and dependencies
- `pyproject.toml` - Python project metadata and build configuration

---

## Web Framework

| Technology | Purpose |
|------------|---------|
| Streamlit | Web UI framework and development server |

### Rationale
Streamlit enables rapid development of data-centric web applications with minimal frontend code. Its reactive model and built-in components align well with the conversational, form-based nature of the application.

---

## AI/LLM Integration

| Provider | SDK | Models |
|----------|-----|--------|
| Anthropic | `anthropic` | Claude Sonnet, Claude Haiku |
| OpenAI | `openai` | GPT-4o, GPT-4o-mini |
| Google | `google-genai` | Gemini Pro, Gemini Flash |

### Architecture
- Abstract `TravelAgent` base class defines the interface
- Provider-specific implementations in `agents/` directory
- Runtime provider selection based on available API keys

---

## Data Layer

| Technology | Purpose |
|------------|---------|
| Pydantic | Data models, validation, and serialization |
| JSON | Session persistence format |

### Key Models
- `Itinerary`, `DayPlan`, `Activity` - Trip structure
- `ItineraryMetadata` - Trip overview and generation info
- `GenerationProgress`, `GenerationState` - Iterative generation tracking
- `Destination`, `TripDestinations` - Location detection

---

## PDF Generation

| Technology | Purpose |
|------------|---------|
| WeasyPrint | HTML/CSS to PDF conversion |
| Jinja2 | HTML template engine |

### Templates
- `magazine.html` - Colorful, image-rich style
- `minimal.html` - Clean, elegant style
- `guidebook.html` - Print-optimized with QR codes

### Dependencies
WeasyPrint requires system libraries (cairo, pango) which are typically pre-installed on Linux systems.

---

## HTTP & Web Scraping

| Technology | Purpose |
|------------|---------|
| httpx | Async HTTP client for API calls |
| BeautifulSoup4 | HTML parsing for blog scraping |

---

## Supporting Libraries

| Technology | Purpose |
|------------|---------|
| Pillow | Image processing and manipulation |
| qrcode | QR code generation for guidebook PDFs |
| keyring | Secure API key storage in system keyring |
| python-dotenv | Environment variable loading from .env files |

---

## Testing

| Technology | Purpose |
|------------|---------|
| pytest | Test framework and runner |

### Commands
```bash
pixi run test  # Run test suite
```

---

## Development Commands

```bash
# Install dependencies
pixi install

# Run the application
pixi run app

# Run tests
pixi run test

# Test imports
pixi run python -c "from ai_travel_planner.models import Itinerary; print('OK')"
```

---

## Change Log

| Date | Change | Rationale |
|------|--------|-----------|
| 2026-01-22 | Initial documentation | Conductor setup - documenting existing stack |
