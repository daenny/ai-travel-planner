# Borneo Travel Planner - Development Guide

## Project Overview

A Streamlit-based travel planning assistant for family trips to Borneo via Kuala Lumpur. Features conversational AI planning, blog content extraction, and PDF generation with multiple styles.

## Quick Start

```bash
# Install dependencies
pixi install

# Run the app
pixi run app
```

## Project Structure

```
src/
├── app.py                 # Streamlit entry point - main UI logic
├── agents/                # AI provider implementations
│   ├── base.py            # Abstract TravelAgent class + system prompt
│   ├── claude_agent.py    # Anthropic Claude
│   ├── openai_agent.py    # OpenAI GPT
│   └── gemini_agent.py    # Google Gemini
├── services/              # External integrations
│   ├── unsplash.py        # Image fetching + caching
│   ├── blog_scraper.py    # HTML scraping for travel tips
│   └── pdf_generator.py   # WeasyPrint PDF generation
├── models/                # Pydantic data models
│   └── itinerary.py       # Itinerary, DayPlan, Activity, etc.
├── storage/               # Persistence
│   └── json_store.py      # JSON file save/load
└── templates/             # Jinja2 HTML templates for PDFs
    ├── magazine.html      # Colorful travel magazine style
    ├── minimal.html       # Clean, elegant style
    └── guidebook.html     # Print-optimized with QR codes
```

## Key Patterns

### Adding a New AI Provider

1. Create `src/agents/new_agent.py`
2. Inherit from `TravelAgent` base class
3. Implement required methods:
   - `chat(message, history)` - streaming generator
   - `generate_itinerary_json(requirements, current_itinerary)` - returns `Itinerary`
   - `name` and `model_id` properties
4. Add to `src/agents/__init__.py`
5. Add provider option in `src/app.py` `get_agent()` function

### Adding a New PDF Style

1. Create `src/templates/newstyle.html` (Jinja2 template)
2. Add enum value to `PDFStyle` in `src/services/pdf_generator.py`
3. Template receives: `itinerary`, `qr_codes`, `b64image` filter

### Blog Integration

The blog scraper can use AI for intelligent extraction:
1. `BlogScraper.scrape_blog(url)` - Basic HTML scraping
2. `BlogScraper.scrape_with_ai(url, agent)` - AI-powered extraction using the travel agent
3. `BlogContent.to_context_string()` - Formats content for AI context

### Data Flow

```
User Chat → Agent.chat() → ChatMessage stored in PlannerSession
         ↓
"Generate Itinerary" → Agent.generate_itinerary_json() → Itinerary model
         ↓
"Generate PDF" → PDFGenerator.generate_pdf() → WeasyPrint → PDF file

Blog URL → BlogScraper.scrape_with_ai() → BlogContent → "Share tips" → Agent context
```

## API Key Storage

API keys can be stored in two ways:

### 1. System Keyring (Recommended)
Keys are securely stored in the OS keyring (GNOME Keyring, KWallet, macOS Keychain, Windows Credential Manager).
- Use the "💾 Save Key" button in the sidebar to store keys
- Keys persist across sessions securely
- Service name: `borneo-travel-planner`

### 2. Environment Variables (Fallback)
Create `.env` file with:
- `ANTHROPIC_API_KEY` - For Claude
- `OPENAI_API_KEY` - For OpenAI
- `GOOGLE_API_KEY` - For Gemini
- `UNSPLASH_ACCESS_KEY` - For images (optional but recommended)

The app checks keyring first, then falls back to environment variables.

## Dependencies

Managed via pixi (conda-forge). Key packages:
- `streamlit` - Web UI
- `anthropic`, `openai`, `google-genai` - AI providers
- `weasyprint` - PDF generation (requires system libs)
- `beautifulsoup4` - Blog scraping
- `pydantic` - Data validation
- `jinja2` - PDF templating
- `qrcode` - QR codes for guidebook style
- `keyring` - Secure API key storage

## Common Tasks

### Modify the AI System Prompt

Edit `SYSTEM_PROMPT` in `src/agents/base.py`. This prompt is shared across all providers.

### Change Itinerary JSON Schema

1. Update Pydantic models in `src/models/itinerary.py`
2. Update `ITINERARY_JSON_PROMPT` in each agent file (claude, openai, gemini)
3. Update PDF templates if new fields need rendering

### Add New Activity Types

Add to `ActivityType` enum in `src/models/itinerary.py`

### Customize PDF Styling

Edit the `<style>` section in the relevant template file in `src/templates/`

## Testing

Run manual testing:
```bash
pixi run app
```

Test imports:
```bash
pixi run python -c "from src.models import Itinerary; print('OK')"
```

## Known Issues

- WeasyPrint requires system libraries (cairo, pango) - usually pre-installed on Linux
- Large blog pages may timeout during scraping

## Code Style

- Type hints throughout
- Pydantic for data validation
- Generator-based streaming for chat responses
- Path objects for file handling
- f-strings for formatting
